#!/usr/bin/env python
import os
import sys
import json
import subprocess
import i3ipc

from jsonschema import validate
from Xlib import X, display, Xutil
from Xlib.ext import randr

from i3workscreen.validationschema import schema

HOME = os.environ.get('HOME')
CONFIG = os.path.join(HOME, '.config', 'i3-workscreen', 'config.json')
i3 = i3ipc.Connection()
d = display.Display()

def logger(message):
    """Writes the message into the linux system log

    :message: string
    """
    message = '[i3-workscreen] ' + message
    sys.stderr.write(message)
    subprocess.run(args=['logger', message], check=True)

def get_outputs(display):
    """Get collection of display outputs

    :returns: array of display output objects
    """
    root = display.screen().root
    resources = root.xrandr_get_screen_resources()._data
    outputs = []

    for output in resources['outputs']:
        _data = display.xrandr_get_output_info(output,
                resources['config_timestamp'])._data

        outputs.append({
            'name': _data['name'],
            'connected': not _data['connection'],
            'dissabled': not _data['crtc']
        });

    return outputs


def get_config(path):
    """fetches user json configuration

    :path: string
    :returns: {
        outputs: [
            {
                name: string,
                xrandr: array<string>,
                workspaces: array<string>
            }
        ]
    }

    """
    try:
        with open(path, 'r') as file:
            dict = json.loads(file.read())
            validate(dict, schema)
    except FileNotFoundError:
        raise RuntimeError('Missing required config.json at {0}'.format(path))
    else:
        return dict

def difference(list, *lists):
    """construct a collection with values of first list argument which are not
    present in any other list arguments provided to the function
    """
    out = []
    isPresent = False
    for item in list:
        isPresent = False
        for list2 in lists:
            if item in list2:
                isPresent = True
                break
        if not isPresent:
            out.append(item)
    return out

def createi3CmdString(outputName, workspaces):
    cmd = ''
    for workspace in workspaces:
        cmd += 'workspace {0}; move workspace to output {1}; '.format(workspace, outputName)
    return cmd

def getBuiltInDisplayOutputName(outputs):
    """detects built-in laptop display output.
    returns first active output name whose name starts either with `eDP` or `LVDS`
    TODO: do you know a better method of detecting this
    (other than manual configuration), let me know please!

    :outputs: array<object>
    :returns: string

    """
    for output in outputs:
        if output['name'].startswith('eDP') or output['name'].startswith('LVDS'):
            return output['name']

def main():
    # Check for extension
    if not d.has_extension('RANDR'):
        raise RuntimeError('server does not have the RANDR extension')

    #xrandr outputs (like HDMI-1, DP-1 etc..)
    outputs = get_outputs(d)
    #identifier of currently focues i3 workspace
    focusedWorkspace = i3.get_tree().find_focused().workspace().name
    config = get_config(CONFIG)
    connectedOutputs = []
    #user configured list of workspace identifiers assigned to particular display output
    connectedOutputWorkspaces = []
    #i3 multi command string which will bind workspaces to correct display outputs
    i3cmd = ''

    for output in outputs:
        outputConf = next(
                filter(lambda o: o['name'] == output['name'], config['outputs']),
                {}
                )

        if 'xrandr' in outputConf and isinstance(outputConf['xrandr'], list):
            output['xrandr'] = outputConf['xrandr']

        if 'workspaces' in outputConf and isinstance(outputConf['workspaces'], list):
            output['workspaces'] = outputConf['workspaces']
        else:
            continue

        index = config['outputs'].index(outputConf)

        if output['connected']:
            connectedOutputs.insert(index, output)
            if 'workspaces' in output:
                connectedOutputWorkspaces.insert(index, output['workspaces'])

    builtInDisplayOutput = getBuiltInDisplayOutputName(connectedOutputs)

    for index,output in enumerate(connectedOutputs):
        #TODO find out how to do the same thing with Xlib
        #witout spawning a shell process?
        xrandrArgs = ['xrandr', '--output', output['name'], '--auto']
        if 'xrandr' in output:
            xrandrArgs = xrandrArgs + output['xrandr']
        subprocess.run(args=xrandrArgs, check=True)

        try:
            nextOutput = connectedOutputs[index + 1]
        except IndexError:
            i3cmd += createi3CmdString(output['name'], output['workspaces'])
            break

        output['workspaces'] = difference(*connectedOutputWorkspaces[index:])
        i3cmd += createi3CmdString(output['name'], output['workspaces'])

    for output in outputs:
        if (not output['connected']  or
           (output['connected'] and not len(output['workspaces']) and config['disableEmptyOutputs'])):
            #TODO find out how to do the same thing with Xlib
            #witout spawning a shell process?
            xrandrArgs = ['xrandr', '--output', output['name'], '--auto']
            xrandrArgs = ['xrandr', '--output', output['name'], '--off']
            subprocess.run(args=xrandrArgs, check=True)

    i3.command(i3cmd)
    i3.command('workspace {0}'.format(focusedWorkspace))




if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger(str(e))
        sys.exit(1);
