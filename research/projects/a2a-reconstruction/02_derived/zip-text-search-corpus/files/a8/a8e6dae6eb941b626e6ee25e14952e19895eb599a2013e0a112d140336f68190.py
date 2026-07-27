import tempfile
import unittest
from pathlib import Path

from towow_fieldkit.store import CaseStore, read_json


class StoreExtensionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/'case'
        self.store=CaseStore.create(self.root,'OPC test','opc-test')
        self.store.add_party('owner','Owner','root:owner')
        self.mandate_path=self.store.issue_mandate('owner',{'permissions':['draft','schedule']})
        self.store.add_relation_version({'R':{},'V':{},'T':{},'A':{},'E':{},'D':{},'O':{}})

    def tearDown(self):
        self.tmp.cleanup()

    def test_revoke_mandate_and_exact_version_stance(self):
        mandate=read_json(self.mandate_path)
        self.store.revoke_mandate('owner',mandate['mandate_id'],actor='owner',reason='scope changed')
        self.assertEqual(read_json(self.mandate_path)['status'],'REVOKED')
        event=self.store.record_stance(party_id='owner',stance='CONDITIONAL',actor='owner',authority_ref='root:owner')
        self.assertTrue(event['payload']['relation_content_hash'])

    def test_attach_evidence_and_scoped_reopen(self):
        src=Path(self.tmp.name)/'evidence.txt'; src.write_text('authoritative readback')
        dst=self.store.attach_evidence(source=src,evidence_type='READBACK',actor='owner')
        self.assertTrue(dst.exists())
        event=self.store.record_scoped_reopen(trigger='MANDATE_REVOKED',affected_nodes=['execution','acceptance'],actor='owner')
        self.assertEqual(event['payload']['affected_nodes'],['acceptance','execution'])


if __name__=='__main__': unittest.main()
