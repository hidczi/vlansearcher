#!/usr/bin/env python3

import telnetlib
import re
import subprocess as sp
import argparse
import signal
import readline


username = 'login'
password = 'passwd'
command = 'show vlan'

# re variables
answer_re = r'^[yYnN]$'
vlan_re = r'(?:[1-9]\d{,2}|[1-3]\d{3}|40(?:[0-8]\d|9[0-4]))$'
ip_re = r'(:?(2[0-4]\d|25[0-5]|[01]?\d\d?)\.){3}(2[0-4]\d|25[0-5]|[01]?\d\d?)$'
hostname_re = r'(:?\d\d-[A-Z]+-[A-Z]+\d+-[A-Z]+-\d$)'

parser = argparse.ArgumentParser(description='vlansearcher')

parser.add_argument('ip', help='IP address or hostname')
parser.add_argument('-s', dest='st', help='Lower range threshold')
parser.add_argument('-f', dest='fn', help='Upper range threshold')

args = parser.parse_args()


def signal_handler(sig, frame):
    print('\r')
    exit(0)


signal.signal(signal.SIGINT, signal_handler)


def to_bytes(line):
    return f'{line}\n'.encode('utf-8')


def value_swapper(start, finish):
    print('\nThe beginning of the range is larger than its end.')
    while True:
        answer = input('Swap values? y/n: ')
        if not re.match(answer_re, answer):
            print('\ninvalid value.')
            continue
        else:
            if answer.lower() == 'n':
                exit(0)
            else:
                return finish, start


def stfn_input(start, finish):
    while True:
        start = input('start number: ')
        finish = input('finish number: ')
        if not re.match(vlan_re, start) or not re.match(vlan_re, finish):
            print('\nInvalid vlan\n')
            exit(1)
        if finish < start:
            start, finish = value_swapper(start, finish)
            break
        else:
            break
    return start, finish


def show_vlans(ip, username, password, command):
    with telnetlib.Telnet(ip) as telnet:
        telnet.expect([b'ogin:', b'sername:'])
        telnet.write(to_bytes(username))
        telnet.read_until(b'assword:')
        telnet.write(to_bytes(password))
        telnet.write(to_bytes(command))
        telnet.read_very_eager()
        telnet.expect([b'>', b'#'], timeout=2)
        result = ""

        while True:
            ind, match, output = telnet.expect([b'[Mm]ore', b'[#>]'], timeout=2)
            output = output.decode("utf-8")
            if re.findall(r'[Ee]rror', output):
                print('\nOS or the vendor is not yet suported\n')
                exit(1)
            result += output
            if ind in (1, -1):
                break
            telnet.write(b" ")

        result = result.split()
        result = [i for i in result if re.findall(r'^\d{1,4}$', i)]
        result = [int(i) for i in result]

    return result


st = args.st
fn = args.fn

if not re.match(ip_re, args.ip) and not re.match(hostname_re, args.ip):
    print(f'\n{args.ip} cannot be an IP address hostname.\n')
    exit(1)

status, result = sp.getstatusoutput('ping -c1 -w2 ' + str(args.ip))
if status != 0:
    print(f'\nThe {args.ip} is unavailable.\n')
    exit(0)


if st is None or fn is None:
    print('\nNot enough arguments\n')
    st, fn = stfn_input(st, fn)


if not re.match(vlan_re, st) or not re.match(vlan_re, fn):
    print('Invalid vlan\n')
    exit(1)
else:
    if int(st) > int(fn):
        st, fn = value_swapper(st, fn)


used_vlans = show_vlans(args.ip, username, password, command)
result_list = list(set(used_vlans) ^ set(range(1, 4095)))
result_list = [i for i in result_list if i >= int(st) and i <= int(fn)]


if len(result_list) == 0:
    print('\nIn the selected range, all vlan numbers are busy')
    exit(0)
else:
    count = 0
    for i in result_list:
        print(f'{i:>4d}', end=' ')
        count += 1
        if count % 20 == 0:
            print('\r')
print('\r')
