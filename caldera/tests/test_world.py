from unittest import TestCase
import json
from caldera.app.simulate.world import World


schema_json = """
{
    "ObservedShare": {
        "src_host": {
            "ref": "ObservedHost"
        },
        "dest_host": {
            "ref": "ObservedHost"
        },
        "share_path": "string",
        "share_name": "string"
    },
    "ObservedSchtask": {
        "status": "string",
        "name": "string",
        "user": {
            "ref": "ObservedUser"
        },
        "cred": {
            "ref": "ObservedCredential"
        },
        "exe_path": "string",
        "arguments": "string",
        "start_time": "datetime",
        "remote_host": {
            "ref": "ObservedHost"
        }
    },
    "ObservedDomainUser": {
        "sid": "string",
        "is_group": "bool",
        "username": "string",
        "domain": {
            "ref": "ObservedDomain"
        },
        "cred": {
            "backref": {
                "ObservedDomainCredential": "user" 
            }
        }
    },
    "ObservedLocalUser": {
        "sid": "string",
        "is_group": "bool",
        "username": "string",
        "host": {
            "ref": "ObservedHost"
        },
        "cred": {
            "backref": {
                "ObservedLocalCredential": "user" 
            }
        }
    },
    "ObservedRat": {
        "executable": "string",
        "host": {
            "ref": "ObservedHost"
        },
        "elevated": "bool"
    },
    "ObservedLocalCredential": {
        "host": {
            "ref": "ObservedHost"
        },
        "user": {
            "ref": "ObservedLocalUser"
        },
        "password": "string"
    },
    "ObservedDomainCredential": {
        "user": {
            "ref": "ObservedDomainUser"
        },
        "domain": {
            "ref": "ObservedDomain"
        },
        "password": "string"
    },
    "ObservedDomain": {
        "windows_domain": "string",
        "dns_domain": "string",
        "hosts": {
          "list": {
            "backref": {
              "ObservedHost": "domain"
            }
          }
        }
    },
    "ObservedHost": {
        "dc" : "bool",
        "dns_domain_name": "string",
        "domain": {
            "ref" : "ObservedDomain"
        },
        "fqdn": "string",
        "local_user_admins": {
            "list": {
                "ref": "ObservedLocalUser"
            }
        },
        "domain_user_admins": {
            "list": {
                "ref": "ObservedDomainUser"
            }
        },
        "cached_local_creds" : {
            "list": {
                "ref": "ObservedLocalCredential"
            }
        },
        "cached_domain_creds" : {
            "list": {
                "ref": "ObservedDomainCredential"
            }
        },
        "hostname": "string",
        "timedelta": {
            "backref": {
                "ObservedTimeDelta": "host"
            }
        }
    },
    "ObservedFile": {
        "path": "string",
        "host": {
            "ref": "ObservedHost"
        },
        "src_path": "string",
        "src_host": {
            "ref": "ObservedHost"
        }
    },
    "ObservedTimeDelta": {
        "seconds": "int",
        "host": {
            "ref": "ObservedHost"
        },
        "microseconds": "int"
    },
    "ObservedConnection": {
        "src":  {
            "ref": "ObservedHost"
        },
        "dest": {
            "ref": "ObservedHost"
        }
    }
}
"""

domain_json = """
[
  {
    "ObservedDomain": {
      "number": 2,
      "fields": [
        {
          "windows_domain": "$unique_greek"
        }
      ]
    }
  },
  {
    "ObservedDomainUser": {
      "number": {
        "$random": [
          30,
          50
        ]
      },
      "fields": [
        {
          "is_group": false
        },
        {
          "username": "$unique_name"
        },
        {
          "domain": "$random_existing"
        },
        {
          "cred": {
            "$new": {
              "fields": [
                {
                  "user": "$parent.id"
                },
                {
                  "domain": "$parent.domain"
                }
              ]
            }
          }
        }
      ]
    }
  },
  {
    "ObservedHost": {
      "number": {
        "$random": [
          50,
          100
        ]
      },
      "fields": [
        {
          "dc": {
            "$bool_prob": 0.05
          }
        },
        {
          "domain": "$random_existing"
        },
        {
          "domain_user_admins": {
            "$match": [
              "domain",
              "domain"
            ],
            "$random_sample": 5
          }
        },
        {
          "cached_domain_creds": {
            "$random_sample": 2
          }
        },
        {
          "timedelta": {
            "$new": {
              "fields": [
                {
                  "host": "$parent.id"
                }
              ]
            }
          }
        }
      ]
    }
  },
  {
    "ObservedRat": {
      "number": 1,
      "fields": [
        {
          "host": "$random_existing"
        },
        {
          "elevated": true
        }
      ]
    }
  }
]
"""


class TestWorld(TestCase):
    def test_generate_domain(self):
        schema = json.loads(schema_json)

        domain = json.loads(domain_json)

        objects = World.generate_domain(schema, domain)
        print(objects)
