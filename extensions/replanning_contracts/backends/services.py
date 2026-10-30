"""Fresh local Redis service for this study only; no existing service discovery.

An empty temporary Docker client config avoids registry credentials/context reuse.
Every managed container, network and volume has a fresh study-only random name.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time

REDIS_IMAGE='redis@sha256:2c933526722b4126a61d5c170f766dc159adf97682f0b1cbbc27b1666ba96d84'
REDIS_IMAGE_TAG='redis:7.2.17-alpine'

class IsolatedRedis:
 def __init__(self,image=REDIS_IMAGE):
  self.image=image;self.password=secrets.token_urlsafe(32)
  self.nonce='replanning-study-'+secrets.token_hex(12)
  self.container=None;self.network=None;self.volume=None
  self.configuration=None;self.port=None;self.cleanup_status={}
  candidates=[Path('/var/run/docker.sock'),Path.home()/'.docker/run/docker.sock']
  self.socket=next((path for path in candidates if path.exists()),None)
  if self.socket is None:raise RuntimeError('No local Docker Unix socket available')

 def command(self,arguments,timeout=60,check=True):
  environment=dict(os.environ)
  for key in ('DOCKER_CONTEXT','DOCKER_HOST','DOCKER_CONFIG','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):
   environment.pop(key,None)
  prefix=['docker','--config',self.configuration.name,'--host','unix://'+str(self.socket)]
  result=subprocess.run(prefix+list(arguments),capture_output=True,text=True,timeout=timeout,env=environment)
  if check and result.returncode:
   message=result.stderr.replace(self.password,'[redacted]').replace(self.configuration.name,'[temporary-config]')
   raise RuntimeError(f'local study Docker {arguments[0]} failed ({result.returncode}): {message}')
  return result

 def client(self,authenticate=True):
  import redis
  from redis.backoff import NoBackoff
  from redis.retry import Retry
  return redis.Redis(host='127.0.0.1',port=self.port,password=self.password if authenticate else None,
   decode_responses=True,protocol=2,socket_connect_timeout=2,socket_timeout=5,
   retry=Retry(NoBackoff(),0))

 def refresh_port(self):
  data=json.loads(self.command(['inspect',self.container,'--format','{{json .NetworkSettings.Ports}}']).stdout)
  bindings=data.get('6379/tcp') or []
  if not bindings:raise RuntimeError('Study-only port publication not ready')
  binding=bindings[0]
  if binding['HostIp']!='127.0.0.1':raise RuntimeError('Study Redis is not loopback-only')
  self.port=int(binding['HostPort'])

 def wait_ready(self):
  deadline=time.monotonic()+20
  while True:
   client=None
   try:
    self.refresh_port();client=self.client()
    if client.ping():return
   except Exception:
    if time.monotonic()>deadline:raise
    time.sleep(.05)
   finally:
    if client is not None:client.close()

 def start(self):
  self.configuration=tempfile.TemporaryDirectory(prefix='study-docker-config-')
  (Path(self.configuration.name)/'config.json').write_text('{"auths":{}}')
  try:
   self.pull_output=self.command(['pull',self.image],timeout=60).stdout
   image=json.loads(self.command(['image','inspect',self.image]).stdout)[0]
   self.image_provenance={key:image.get(key) for key in ('Id','RepoDigests','Architecture','Os','Created')}
   self.resolved_image=next((item for item in image.get('RepoDigests',[]) if item.startswith('redis@')),self.image)
   self.network=self.command(['network','create',self.nonce+'-network']).stdout.strip()
   self.volume=self.command(['volume','create',self.nonce+'-data']).stdout.strip()
   self.container=self.command(['run','--detach','--name',self.nonce,'--network',self.network,
    '--publish','127.0.0.1::6379','--mount','type=volume,source='+self.volume+',target=/data',
    self.resolved_image,'redis-server','--appendonly','yes','--appendfsync','always','--save','',
    '--protected-mode','yes','--requirepass',self.password]).stdout.strip()
   self.wait_ready();return self
  except BaseException:
   self.stop();raise

 def restart(self):
  self.command(['restart',self.container],timeout=30)
  self.wait_ready()

 def metadata(self):
  client=self.client()
  try:
   import redis
   server=client.info('server')
   return dict(image=self.image_provenance,resolved_image=self.resolved_image,
    redis_version=server['redis_version'],redis_py_version=redis.__version__,server_os=server['os'],server_arch_bits=server['arch_bits'],
    binding='127.0.0.1, ephemeral host port',study_only_random_credential=True,
    docker_client_config='Fresh temporary empty auth config; explicit local Unix socket',
    persistence=client.config_get('appendonly')|client.config_get('appendfsync'),
    network='Fresh dedicated Docker bridge with only the study server; loopback host publication',volume='Fresh study-only volume')
  finally:client.close()

 def stop(self):
  if self.configuration is None:return
  for kind,identity,arguments in [('container',self.container,['rm','--force']),('volume',self.volume,['volume','rm']),('network',self.network,['network','rm'])]:
   if identity:
    result=self.command(arguments+[identity],check=False,timeout=30)
    self.cleanup_status[kind]=result.returncode==0
  self.configuration.cleanup();self.configuration=None

 def __enter__(self):return self.start()
 def __exit__(self,*_):self.stop()
