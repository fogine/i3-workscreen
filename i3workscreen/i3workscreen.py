#!/usr/bin/env python
import argparse
import os
import re
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

def edid_descriptor_text(block):
    """decodes the text of an EDID display descriptor

    :block: bytes (18 bytes long)
    :returns: string
    """
    return block[5:18].split(b'\n')[0].decode('ascii', 'replace').strip()

def parse_edid(edid):
    """extracts monitor identification from raw EDID data

    :edid: bytes
    :returns: {
        model: string|None,
        serial: string|None
    }
    """
    out = {'model': None, 'serial': None}

    if len(edid) < 128:
        return out

    for offset in range(54, 126, 18):
        block = edid[offset:offset + 18]
        # display descriptors start with three zero bytes, byte 3 is the tag
        if block[0:3] != b'\x00\x00\x00':
            continue
        if block[3] == 0xFC:
            out['model'] = edid_descriptor_text(block)
        elif block[3] == 0xFF:
            out['serial'] = edid_descriptor_text(block)

    # fall back to the numeric serial number when no serial descriptor exists
    if not out['serial']:
        serial = int.from_bytes(edid[12:16], 'little')
        if serial:
            out['serial'] = str(serial)

    return out

def get_edid(display, output):
    """fetches raw EDID data of a display output

    :returns: bytes
    """
    atom = display.intern_atom('EDID')
    prop = display.xrandr_get_output_property(output, atom,
            X.AnyPropertyType, 0, 128)
    return bytes(prop.value)

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
            'edid': parse_edid(get_edid(display, output)),
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

def output_matches_config(output, outputConf):
    """returns True when the configuration entry describes the display output.
    Entries with `edid` are matched by the monitor identification,
    entries without it by the output name.
    """
    if 'edid' in outputConf:
        return all(output['edid'].get(key) == value
                for key, value in outputConf['edid'].items())
    return outputConf.get('name') == output['name']

def assign_output_configs(outputs, config):
    """sets `conf` (configuration entry or {}) and `confIndex` of each
    display output. A configuration entry is assigned to one output at most.
    """
    claimed = set()
    for output in outputs:
        output['conf'] = {}
        output['confIndex'] = None
        if not output['connected']:
            continue
        for index, outputConf in enumerate(config['outputs']):
            if index not in claimed and output_matches_config(output, outputConf):
                claimed.add(index)
                output['conf'] = outputConf
                output['confIndex'] = index
                break

def output_reference_matches(output, reference):
    """returns True when `reference` is the output name or the model or serial
    of the monitor connected to it
    """
    return reference in (output['name'],
            output['edid']['model'], output['edid']['serial'])

def resolve_xrandr_args(args, outputs):
    """replaces `{reference}` arguments with the name of the connected display
    output the reference points at (see output_reference_matches). An argument
    whose reference is not connected is dropped together with the option
    preceding it.
    """
    out = []
    for arg in args:
        match = re.fullmatch(r'\{(.+)\}', arg)
        if not match:
            out.append(arg)
            continue
        target = next(filter(lambda o: o['connected']
            and output_reference_matches(o, match.group(1)), outputs), None)
        if target is None:
            logger('xrandr argument {0} does not match any connected display output, ignoring it'.format(arg))
            if out:
                out.pop()
            continue
        out.append(target['name'])
    return out

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

def getVisibleWorkspacesPerOutput():
    """returns hash of outputs and their visible(active) workspaces
    :returns: {
        output<string>: workspace<string>,
    }
    """
    output = {}
    for workspace in i3.get_workspaces():
        if workspace.visible and not workspace.output in output:
            output[workspace.output] = workspace.name
    return output

def getWorkspaceWithWindowPerOutput():
    """returns hash of outputs and their visible(active) workspaces

    :returns: {
        output<string>: workspace<string>,
    }
    """
    out = {}

    for con in i3.get_tree().leaves():
        if con.type == 'con':
            output = con.workspace().ipc_data['output']
            workspaceName = con.workspace().name
            if not output in out:
                out[output] = workspaceName

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
    enabledOutputs = list(filter(lambda output: (output['dissabled'] != True), outputs))
    if len(enabledOutputs) <= 1:
        return False

    for index,output in enumerate(enabledOutputs):
        if index > 0:
            if output['x'] != enabledOutputs[index-1]['x'] or output['y'] != enabledOutputs[index-1]['y']:
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
    #dictionary of connected outputs and their current workspace name
    visibleWorkspaces = getVisibleWorkspacesPerOutput()
    isFocusedWorkspaceLost = True
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

    assign_output_configs(outputs, config)

    for output in outputs:
        outputConf = output['conf']

        if 'xrandr' in outputConf and isinstance(outputConf['xrandr'], list):
            output['xrandr'] = resolve_xrandr_args(outputConf['xrandr'], outputs)

        if 'workspaces' in outputConf and isinstance(outputConf['workspaces'], list):
            output['workspaces'] = outputConf['workspaces']
        else:
            continue

        index = output['confIndex']

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

        if focusedWorkspace in output['workspaces']:
            isFocusedWorkspaceLost = False

        try:
            nextOutput = connectedOutputs[index + 1]
        except IndexError:
            i3cmd += createi3CmdString(output['name'], output['workspaces'])
            break

        output['workspaces'] = difference(*connectedOutputWorkspaces[index:])
        i3cmd += createi3CmdString(output['name'], output['workspaces'])

    for output in outputs:
        if (not output['connected']  or
           (output['connected'] and not len(output.get('workspaces', [])) and config['disableEmptyOutputs'])):
            xrandr['disabled'] += ['--output', output['name'], '--off']


    args = ['xrandr']

    if shellArgs.toggle:
        if len(connectedOutputs) > 1 and not areDisplayOutputsCloned(connectedOutputs):
            args += xrandr['cloned']
        elif len(connectedOutputs) > 1:
            args += xrandr['extended'] + xrandr['disabled']
    else:
        args += xrandr['extended'] + xrandr['disabled']


    if isFocusedWorkspaceLost:
        for key, value in visibleWorkspaces.items():
            if value != focusedWorkspace:
                focusedWorkspace = value
                break

    #TODO find out how to do the same thing with Xlib
    #witout spawning a shell process?
    subprocess.run(args=args, check=True) #xrandr
    i3.command(i3cmd)

    activeWorkspaces = getWorkspaceWithWindowPerOutput()

    for output in connectedOutputs:
        # output does not have any workspace
        #aka. output was stolen all workspaces by higher priority outputs
        if not len(output['workspaces']):
            continue

        outputConf = output['conf']
        # None when no workspace of the output has any window in it
        activeWorkspace = activeWorkspaces.get(output['name'])
        visibleWorkspace = visibleWorkspaces.get(output['name'], activeWorkspace)
        # if the workspace should be in the current output
        # set it as the active workspace
        if visibleWorkspace in outputConf['workspaces']:
            i3.command('workspace {0}'.format(visibleWorkspace))
        #else set as the active workspace first workspace which belongs to the output
        #and has any window in it
        elif activeWorkspace is not None:
            i3.command('workspace {0}'.format(activeWorkspace))

    i3.command('workspace {0}'.format(focusedWorkspace))




if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger(str(e))
        sys.exit(1);
