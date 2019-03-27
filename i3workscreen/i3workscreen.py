#!/usr/bin/env python
import argparse
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
    primaryOutput = root.xrandr_get_output_primary().output
    outputs = []

    for output in resources['outputs']:
        _data = display.xrandr_get_output_info(output,
                resources['config_timestamp'])._data
        x = y = 0

        if _data['crtc']:
            crtcInfo = display.xrandr_get_crtc_info(_data['crtc'],
                    resources['config_timestamp'])
            x = crtcInfo.x
            y = crtcInfo.y

        outputs.append({
            'isPrimary': output == primaryOutput,
            'name': _data['name'],
            'connected': not _data['connection'],
            'dissabled': not _data['crtc'],
            'x': x,
            'y': y
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
    with open(path, 'r') as file:
        dict = json.loads(file.read())
        validate(dict, schema)
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

def areDisplayOutputsCloned(outputs):
    """returns True whether more than one display output points at the same
    framebuffer address

    :outputs: array
    :returns: boolean

    """
    for index,output in enumerate(outputs):
        if index > 0:
            if output['x'] != outputs[index-1]['x'] or output['y'] != outputs[index-1]['y']:
                return False

    return True

def getShellArgs():
    parser=argparse.ArgumentParser(
            description='Required configuration file is fetched from: `$HOME/.config/i3-workscreen/config.json`')
    parser.add_argument('--toggle', action='store_true', help='Toggles between mirrored & extended display mode')
    return parser.parse_args()

def getCloneCandidate(outputs):
    """
    :returns single connected & enabled display output which will be cloned
    """
    index = None
    for i,output in enumerate(outputs):
        if output and index is None:
            index = i
        if output['isPrimary']:
            return output

    if index is None:
        raise Exception('No connected display outputs detected.')

    return outputs[index]

def main():
    # Check for extension
    if not d.has_extension('RANDR'):
        raise Exception('server does not have the RANDR extension')

    try:
        config = get_config(CONFIG)
    except FileNotFoundError:
        logger('No configuration file found at {0}'.format(CONFIG))
        return
    shellArgs=getShellArgs()
    #xrandr outputs (like HDMI-1, DP-1 etc..)
    outputs = get_outputs(d)
    #identifier of currently focues i3 workspace
    focusedWorkspace = i3.get_tree().find_focused().workspace().name
    xrandr = {
        'cloned': [],
        'extended': [],
        'disabled': []
    }
    connectedOutputs = []
    enabledOutputs = []
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

    outputCloneCandidate = getCloneCandidate(connectedOutputs)

    for index,output in enumerate(connectedOutputs):
        xrandr['extended'] += ['--output', output['name'], '--auto']
        xrandr['cloned'] += xrandr['extended'][:]

        if output['name'] != outputCloneCandidate['name']:
            xrandr['cloned'] += ['--same-as', outputCloneCandidate['name']]

        if 'xrandr' in output:
            xrandr['extended'] += output['xrandr']

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
            xrandr['disabled'] += ['--output', output['name'], '--off']


    args = ['xrandr']

    if shellArgs.toggle:
        if len(connectedOutputs) > 1 and not areDisplayOutputsCloned(connectedOutputs):
            args += xrandr['cloned'] + xrandr['disabled']
        elif len(connectedOutputs) > 1:
            args += xrandr['extended'] + xrandr['disabled']
    else:
        args += xrandr['extended'] + xrandr['disabled']

    #TODO find out how to do the same thing with Xlib
    #witout spawning a shell process?
    subprocess.run(args=args, check=True) #xrandr
    i3.command(i3cmd)
    i3.command('workspace {0}'.format(focusedWorkspace))




if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger(str(e))
        sys.exit(1);
