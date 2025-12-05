<div align="center">
  <br>
  <img src="./img/logo.png" alt="Logo" width="256">
  <br>
</div>

<div id="toc">  <ul align="center" style="list-style: none">
    <summary>
      <h1 style="border-bottom: 0; display: inline-block;">
        <b>ESPHome IR Manager</b><br>
          <sub>for Home Assistant</sub></h1>
    </summary>
  </ul>
</div>

<hr>
<div align="center">

`» ESPHome IR remote as 'virtual' remote entity`

`» Better device / commands management`

</div>

{% if not installed %}

## Installation (Easy)
[![ADD][hacs2]](https://ha-link.heyfordy.de/redirect/hacs_repository/?owner=Bitte-ein-Git&repository=ha_esphome_rc&category=integration)
## Installation (Manual)
1. Add this Repository to HACS:
   - HACS > 3 dots > "Add custom repository"
   - URL: `Bitte-ein-Git/ha_esphome_rc`
   - Type: Integration

2. Select "**🗿• ESPHome IR Manager 🛠️**".

<hr>

> After installation you **have to restart Home Assistant**

{% endif %}

{% if installed and not configured %}

## Configuration
> [!NOTE]
> After installation you **have to restart Home Assistant**

### Easy Configuration (Link to Config Screen)
[![ADD][setup2]](https://ha-link.heyfordy.de/redirect/config_flow_start/?domain=esphome_rc)
### Manual Configuration
1. Add a new config entry via UI:
   - Go to your Home Assistant **Settings**
   - Select "**Devices & services**"
   - At the bottom right select "**+ Add integration**"

2. Select "**🗿• ESPHome IR Manager 🛠️**".

{% endif %}

<hr><br>

<br><hr>

<div align="center">
  <a href="https://esphome.io"><img src="https://media.esphome.io/made-for-esphome/made-for-esphome-dark.svg" alt="Made for ESPHome" style="width:33%;"></a>
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge" alt="HACS" style="height:5%;"></a>
  <a href="https://ha-link.heyfordy.de/redirect/hacs_repository/?owner=Bitte-ein-Git&repository=ha_esphome_rc&category=integration"><img src="https://img.shields.io/badge/HACS-%23ff8c00.svg?style=for-the-badge&logo=homeassistantcommunitystore&label=Add%20Repository%20to" alt="ADD TO REPO" style="height:5%;"></a>
  <a href="https://ha-link.heyfordy.de/redirect/config_flow_start/?domain=esphome_rc"><img src="https://img.shields.io/badge/HA-%2318BCF2.svg?style=for-the-badge&logo=homeassistant&label=Add%20Integration%20to" alt="START CONFIG FLOW" style="height:5%;"></a>
</div>

[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[hacs1]: https://img.shields.io/badge/HACS-%23ff8c00.svg?style=for-the-badge&logo=homeassistantcommunitystore&label=Add%20Repository%20to
[hacs2]: https://ha-link.heyfordy.de/badges/hacs_repository.svg
[setup1]: https://img.shields.io/badge/HA-%2318BCF2.svg?style=for-the-badge&logo=homeassistant&label=Add%20Integration%20to
[setup2]: https://ha-link.heyfordy.de/badges/config_flow_start.svg
