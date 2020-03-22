import pytest


@pytest.mark.usefixtures(
    'init_base_world'
)
class TestFileSvc:

    def test_check_payload_obfuscation(self, loop, data_svc, file_svc, ability, demo_operation):
        orig_payload_name = 'predeterminedobfuscation.exe'
        mapped_payload_name = 'unittestobfuscation'

        # make mapping in payload map
        demo_operation.payloads_map['to_real_payload'][mapped_payload_name] = orig_payload_name
        demo_operation.obfuscate_payloads = True
        demo_operation.set_start_details()  # set ID
        loop.run_until_complete(data_svc.store(demo_operation))

        identifier = "%d-12345" % demo_operation.id
        payload, display_name = loop.run_until_complete(file_svc.check_payload_obfuscation(identifier, mapped_payload_name))
        assert payload == orig_payload_name
        assert display_name == mapped_payload_name
