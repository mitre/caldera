# plugins/studentlab/app/student_assign.py
# Fill these with real ability UUIDs visible in your Caldera instance.
# Tip: you can list abilities via the data service or REST and copy their ids.

STUDENT_ABILITIES = {
    "alice": {
        "abilities": [
            # discovery examples (replace with your actual UUIDs)
            "36eecb80-ede3-442b-8774-956e906aff02",  # Identify active user (example)
            "9a30740d-3aa8-4c23-8efa-d51215e8a5b9",  # Scan WiFi networks (example)
        ]
    },
    "bob": {
        "abilities": [
            # lateral-movement / collection etc (use real IDs)
            "4f7d21c9-ea31-4943-ad8a-efbbeeccdd7d",
            "2afae782-6d0a-4fbd-a6b6-d1ce90090eac"
        ]
    },
}
