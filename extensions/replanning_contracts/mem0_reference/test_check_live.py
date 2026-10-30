"""Live-checker forgery controls; original toy values, no raw corpus mutation."""
import copy,unittest
import check
import check_live

class LiveEvidenceForgeries(unittest.TestCase):
    def test_rejects_false_success_instead_of_actual_baseline_exit(self):
        row=dict(is_baseline=True,expected_returncode=87,child_returncode=0,child_public_stdout='',after=[])
        with self.assertRaisesRegex(check.VerificationError,'Child exit status mismatch'):
            check_live.process_check(row)

    def test_rejects_used_response_bypassing_exact_filter(self):
        response={'memory':[dict(id='0',text='Synthetic exact fact.',attributed_to='user',linked_memory_ids=[])]}
        before=[dict(id='old',memory='Synthetic exact fact.')]
        check_live.response_check(response,{'memory':[]},before,'exact_admission','fresh_model')
        with self.assertRaisesRegex(check.VerificationError,'Raw/used exact-admission response mismatch'):
            check_live.response_check(response,copy.deepcopy(response),before,'exact_admission','fresh_model')

    def test_rejects_copied_baseline_value_change(self):
        baseline=[dict(id='old',memory='Synthetic original fact.')]
        check_live.copy_check(copy.deepcopy(baseline),baseline)
        forged=[dict(id='old',memory='Different synthetic fact.')]
        with self.assertRaisesRegex(check.VerificationError,'Copied baseline snapshot differs'):
            check_live.copy_check(forged,baseline)

if __name__=='__main__':unittest.main()
