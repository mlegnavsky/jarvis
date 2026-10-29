import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('firmware_bridge_policy',Path(__file__).parents[1]/'policy.py')
policy=importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
TARGET='voice.yaml'

class PolicyTests(unittest.TestCase):
    def test_only_configured_target_and_fixed_ota_supported(self):
        self.assertEqual(policy.authorize('firmware/install',{'configuration':TARGET},[TARGET]),{'configuration':TARGET,'force_local':True,'port':'OTA','bootloader':False})
        for command,args in [('devices/get_config',{}),('firmware/compile',{'configuration':'secrets.yaml'}),('firmware/install',{'configuration':TARGET,'port':'192.0.2.1'}),('firmware/install',{'configuration':TARGET,'bootloader':True}),('firmware/compile',{'configuration':TARGET,'force_local':False})]:
            with self.assertRaises(ValueError):policy.authorize(command,args,[TARGET])
    def test_job_reads_require_owned_target_and_drop_output_secrets(self):
        job={'job_id':'abc','configuration':TARGET,'status':'completed','exit_code':0,'output':['secret'],'error':'private secret','source_pin_sha256':'secret'}
        clean=policy.redact_result('firmware/get_job',job,[TARGET],{'job_id':'abc'})
        self.assertEqual(clean['job_id'],'abc');self.assertNotIn('secret',str(clean))
        with self.assertRaises(ValueError):policy.redact_result('firmware/get_job',{**job,'configuration':'other.yaml'},[TARGET],{'job_id':'abc'})
    def test_device_list_is_filtered_and_minimized(self):
        result=policy.redact_result('devices/list',{'configured':[{'configuration':TARGET,'name':'voice','expected_config_hash':'1234abcd','runtime_state':{'state':'online','deployed_config_hash':'1234abcd','ip_addresses':['private']}},{'configuration':'other.yaml'}],'importable':[{'name':'private'}]},[TARGET],{})
        self.assertEqual(len(result['configured']),1);self.assertNotIn('private',str(result));self.assertEqual(result['importable'],[])
    def test_jobs_filter_to_requested_configuration(self):
        with self.assertRaises(ValueError):policy.authorize('firmware/get_jobs',{},[TARGET])
        result=policy.redact_result('firmware/get_jobs',[{'configuration':TARGET,'job_id':'a'},{'configuration':'other.yaml','job_id':'b'}],[TARGET],{'configuration':TARGET})
        self.assertEqual([j['job_id'] for j in result],['a'])
