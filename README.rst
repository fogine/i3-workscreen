This utility is targeted to users using i3wm on their laptops who frequently jump between multiple (multi-)monitor setups.  

For example single display output when you are on road, triple-monitor setup at work and two-monitor setup at home.

**i3-workscreen** executable should be triggered by **udev** rule which will listen for specific events caused by plugging/unplugging display output cable(s) (eg.: **HDMI**). The utility will then reassign existing workspaces based on your **json** configuration.

An example of the **udev** rule is provided in the root of the git repository and should be EDITED by the user and copied to **/etc/udev/rules.d/98-monitor-hotplug.rules** on you system.

Installation:
-------------

.. code-block:: bash
    
    /home/user> pip install https://github.com/fogine/i3-workscreen


Configuration:
--------------

**i3-workscreen** fetches configuration from **$HOME/.config/i3-workscreen/config.json**.  

The bellow configuration example shows setup of maximum of three monitors. In this case **eDP-1** is my laptop screen and **HDMI-1** & **DP-1** are external monitors.

Four scenarios may happen with the configuration:

1. **eDP-1** connected, **HDMI-1** & **DP-1** disconnected

   In this case all workspaces are assigned to the single screen
2. **eDP-1** connected, **HDMI-1** connected, **DP-1** disconnected 

   In this case workspaces 1-5 belong to **eDP-1** and workspaces 6-0 belong to **HDMI-1**
3. **eDP-1** connected, **HDMI-1** disconnected, **DP-1** connected 

   In this case workspaces 1-5 belong to **DP-1** and workspaces 6-0 belong to **eDP-1**
4. **eDP-1** connected, **HDMI-1** connected, **DP-1** connected 

   In this case workspaces 1-5 belong to **DP-1** and workspaces 6-0 belong to **HDMI-1**.
   **eDP-1** was stolen all workspaces by higher priority outputs and because **disableEmptyOutputs=true**, **eDP-1** display output will be disabled. if the option was set to **false**, the output would be enabled and you could interact with the connected monitor and **i3** would assign to it first **empty** workspace (workspace without any windows in it)

.. code-block:: json

    {
        "disableEmptyOutputs": true,
        "outputs": [
            {
                "name": "eDP-1",
                "workspaces": [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0" ]
            },
            {
                "name": "HDMI-1",
                "xrandr": ["--above", "eDP-1"],
                "workspaces": [ "6", "7", "8", "9", "0" ]
            },
            {
                "name": "DP-1",
                "workspaces": ["1", "2", "3", "4", "5"]
            }
        ]
    }
