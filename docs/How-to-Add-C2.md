How to Add C2
=============

Building your own c2 channel allows you to add custom functionality to CALDERA.  C2 is now part of core CALDERA, and as a result there are a few places you'll need to  implement your new c2 functionality.

## Server side
1. Add a contact method on the server side
    1. Create a file: /app/contacts/contact_<c2_name>.py
    2. Implement server side functionality into the new file
2. Register your contact in app_svc.py
    1. Import the file from 1.i. into app_svc.py
    2. Add your c2 to the register_contacts function
3. Add required configuration variables to conf/default.yml

## Client side
1.  Implement communications with the server
    1. Create a file: sandcat/gocat/contact/<c2_name>.go
    2. In your new file, implement functions that are defined in: sandcat/gocat/contact/contact.go
2. Add a check for external dependencies for go
    1. Create sandcat/app/extensions/contact/<c2_name>.py
    2. This file should reference all external dependencies that your c2 will need.  Reference ./gist.py for an example.
    
## Agent side
The agent will need to know that you want to run this new c2 functionality.  To do this you'll need to add a header to the script when you start your agent.  
Header format:
* Linux: -H "c2:<c2_name>"
* Windows: $wc.Headers.add("c2", "<c2_name>");

You'll need to add your new c2 functionality to the agent standard configurations in sandcat/data/abilities/initial-access/.  To do this you'll need to:
1. Get a new UUID (https://www.uuidgenerator.net/ is one option)
2. Create sandcat/data/abilities/initial-access/<new_uuid>.yml
3. Add all the fields required to the new file.  Reference for structure: 2f34977d-9558-4c12-abad-349716777c6b.yml
