How to Build Plugins
================

Building your own plugin allows you to add custom functionality to CALDERA. 

A plugin can be nearly anything, from a RAT/agent (like 54ndc47) to a new GUI or a collection of abilities that you want to keep in "closed-source". 

Plugins are stored in the plugins directory. If a plugin is also listed in the local.yml file, it will be loaded into CALDERA each time the server starts. A plugin is loaded through its hook.py file, which is "hooked" into the core system via the server.py (main) module.

This walkthrough assumes you're pulling from the master branch.

## Creating the structure

Start by creating a new directory called "abilities" in CALDERA's plugins directory. In this directory, create a hook.py file and ensure it looks like this:
```python
name = 'Abilities'
description = 'A sample plugin for demonstration purposes'
address = None


async def enable(services):
    pass
```

The name should always be a single word, the description a phrase, and the address should be None, unless your plugin exposes new GUI pages. Our example plugin will be called "abilities".

## The _enable_ function

The enable function is what gets hooked into CALDERA at boot time. This function accepts one parameter:

1. **services**: a list of core services that CALDERA creates at boot time, which allow you to interact with the core system in a safe manner. 

Core services can be found in the app/services directory.

## Writing the code

Now it's time to fill in your own enable function. Let's start by appending a new REST API endpoint to the server. When this endpoint is hit, we will direct the request to a new class (AbilityFetcher) and function (get_abilities). The full hook.py file now looks like:
```python
from aiohttp import web

name = 'Abilities'
description = 'A sample plugin for demonstration purposes'
address = None


async def enable(services):
    app = services.get('app_svc').application
    fetcher = AbilityFetcher(services)
    app.router.add_route('*', '/get/abilities', fetcher.get_abilities)


class AbilityFetcher:

    def __init__(self, services):
        self.services = services

    async def get_abilities(self, request):
        abilities = await self.services.get('data_svc').locate('abilities')
        return web.json_response(dict(abilities=[a.display for a in abilities]))
```

Now that our initialize function is filled in, let's add the plugin to the default.yml file and restart CALDERA. Once running, in a browser or via cURL, navigate to 127.0.0.1:8888/get/abilities. If all worked, you should get a JSON response back, with all the abilities within CALDERA. 

## Making it visual

Now we have a usable plugin, but we want to make it more visually appealing. 

Start by creating a "templates" directory inside your plugin directory (abilities). Inside the templates directory, create a new file called abilities.html. Ensure the content looks like:
```html
<div id="abilities-new-section" class="section-profile">
    <div class="row">
        <div class="topleft duk-icon"><img onclick="removeSection('abilities-new-section')" src="/gui/img/x.png"></div>
        <div class="column section-border" style="flex:25%;text-align:left;padding:15px;">
            <h1 style="font-size:70px;margin-top:-20px;">Abilities</h1>
        </div>
        <div class="column" style="flex:75%;padding:15px;text-align: left">
            <div>
                {% for a in abilities %}
                    <pre style="color:white">{{ a }}</pre>
                    <hr>
                {% endfor %}
            </div>
        </div>
    </div>
</div>
```

Then, back in your hook.py file, let's fill in the address variable and ensure we return the new abilities.html page when a user requests 127.0.0.1/get/abilities. Here is the full hook.py:

```python
from aiohttp_jinja2 import template, web

name = 'Abilities'
description = 'A sample plugin for demonstration purposes'
address = '/plugin/abilities/gui'

async def enable(services):
    app = services.get('app_svc').application
    fetcher = AbilityFetcher(services)
    app.router.add_route('*', '/plugin/abilities/gui', fetcher.splash)
    app.router.add_route('GET', '/get/abilities', fetcher.get_abilities)


class AbilityFetcher:
    def __init__(self, services):
        self.services = services
        self.auth_svc = services.get('auth_svc')

    async def get_abilities(self, request):
        abilities = await self.services.get('data_svc').locate('abilities')
        return web.json_response(dict(abilities=[a.display for a in abilities]))

    @template('abilities.html')
    async def splash(self, request):
        await self.auth_svc.check_permissions(request)
        abilities = await self.services.get('data_svc').locate('abilities')
        return(dict(abilities=[a.display for a in abilities]))
```
Restart CALDERA and navigate to the home page. Be sure to run ```server.py```
with the ```--fresh``` flag to flush the previous object store database. 

You should see a new "abilities" tab at the top, clicking on this should navigate you to the new abilities.html page you created. 