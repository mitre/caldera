from marshmallow import fields, schema


class AbilityUploadRequestSchema(schema.Schema):
    """Schema for the multipart upload endpoint expecting a YAML file containing an ability.

    The `file` field is a raw file upload. The metadata contains a short description and an
    example YAML payload that matches the tests in `tests/api/v2/handlers/test_ability_upload.py`.
    """

    file = fields.Raw(required=True, metadata={
        'type': 'file',
        'description': 'A YAML file containing one ability (or a list with one ability). The tests send a YAML list with a single ability entry.',
        'example': (
            "- id: upload-test-001\n"
            "  name: Uploaded Test Ability\n"
            "  description: An ability uploaded via YAML file\n"
            "  tactic: discovery\n"
            "  technique_id: T1082\n"
            "  technique_name: System Information Discovery\n"
            "  executors:\n"
            "  - name: sh\n"
            "    platform: linux\n"
            "    command: uname -a\n"
        ),
        'example_alternative': (
            "- ability_id: upload-test-002\n"
            "  name: Uploaded Test Ability 2\n"
            "  description: An ability using ability_id key\n"
            "  tactic: collection\n"
            "  technique_id: T1005\n"
            "  technique_name: Data from Local System\n"
            "  executors:\n"
            "  - name: sh\n"
            "    platform: linux\n"
            "    command: ls -la\n"
        )
    })
