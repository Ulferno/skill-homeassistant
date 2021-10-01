# <img src='../docs/home-assistant.png' card_color='#000000' width='50' height='50' style='vertical-align:bottom'/> Home Assistant
Awaken your home - Control Home Assistant

## About
[Home Assistant](https://www.home-assistant.io/) skill include [Voight Kampff tests](https://mycroft-ai.gitbook.io/docs/skill-development/voight-kampff).
To achieve a same development envinroment is needed to add a specific "dummy/testing" componens to your running HA instalation.
When test is run, then skill behave is tested along side with comunication between Mycroft <> HA and also HA actions to each utterance.

## HA Configuration - configuration.yaml
[configuration.yaml](ci/HA/configuration.yaml) contain all necessary dummy entities in HA.

## HA Configuration - automation.yaml
[automations.yaml](ci/HA/automations.yaml) contain dummy automations entities in HA.

*Note: Put automation into automation.yaml only when your configuration.yaml contain `automation: !include automations.yaml` otherwise put it directly into `configuration.yaml`.*

## HA Configuration - .storage
[.storage](ci/HA/.storage) contain copy of dummy instance of HA configuration database for use with CI.
If created new, long live token must be newly generated before copying .storage there so the token is stored also in it.

## Usage - offline usage
Whole testing can be used offline.
- Apply configurations from above.
- Add new logn access token to your HA.
- Apply token to `settings.json` in home assistant skill.
- Check if skill comunicate with HA
- Run these commands:
```
mycroft-skill-testrunner vktest  clear
mycroft-skill-testrunner vktest -t homeassistant.mycroftai
```
More informations about VK tests at [mycroft-ai.gitbook.io](https://mycroft-ai.gitbook.io/docs/skill-development/voight-kampff/test-runner)

*Note: Before each run, is better to retart HA and check if all dummy/test values/states are in initial position.*

## Usage - online usage aka Github Actions
Enable [Github pages](https://guides.github.com/features/pages/) and Github Actions for your repo.

In settings of your fork, set publish dir to branch `gh-pages` as `/root`. Alure reports then will be accesible from [https://*YOUR_NAME*.github.io/skill-homeassistant/](https://mycroftai.github.io/skill-homeassistant/)

Workflow will pull latest Mycroft-core from git and Home assistant ver. 2021.9 from pip.
Directory `test/ci/HA` contain Home Assistant configuration with Long live action token, token is set inside [workflow](.github/workflows/build.yaml) as `HASS_TOKEN`.

Overal result will look like this:
# <img src='../docs/github_actions.png' card_color='#000000' width='250' height='200' style='vertical-align:bottom'/>

*Note: VK TEST report state show if an allure report was gerated, not if it was succesful. You have to click on details, it will redirect you to corresponding allure test so You can check it.*

# <img src='../docs/allure_results.png' card_color='#000000' width='1119' height='1032' style='vertical-align:bottom'/>

Workflow should run on both, Commits and PRs.
