# Wizard Kit PE: Functions - Disk

from functions.common import *
import partition_uids

# Regex
REGEX_BAD_PARTITION = re.compile(r'(RAW|Unknown)', re.IGNORECASE)
REGEX_DISK_GPT = re.compile(
    r'Disk ID: {[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+}',
    re.IGNORECASE)
REGEX_DISK_MBR = re.compile(r'Disk ID: [A-Z0-9]+', re.IGNORECASE)
REGEX_DISK_RAW = re.compile(r'Disk ID: 00000000', re.IGNORECASE)

def assign_volume_letters():
    with open(DISKPART_SCRIPT, 'w') as script:
        for vol in get_volumes():
            script.write('select volume {}\n'.format(vol['Number']))
            script.write('assign\n')
    
    # Remove current letters
    remove_volume_letters()
    
    # Run script
    try:
        run_program(['diskpart', '/s', DISKPART_SCRIPT])
    except subprocess.CalledProcessError:
        pass

def get_boot_mode():
    boot_mode = 'Legacy'
    try:
        reg_key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r'System\CurrentControlSet\Control')
        reg_value = winreg.QueryValueEx(reg_key, 'PEFirmwareType')[0]
        if reg_value == 2:
            boot_mode = 'UEFI'
    except:
        boot_mode = 'Unknown'
    
    return boot_mode

def get_disk_details(disk):
    details = {}
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('select disk {}\n'.format(disk['Number']))
        script.write('detail disk\n')
    
    try:
        # Run script
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        # Remove empty lines
        tmp = [s.strip() for s in output.splitlines() if s.strip() != '']
        # Set disk name
        details['Name'] = tmp[4]
        # Split each line on ':' skipping those without ':'
        tmp = [s.split(':') for s in tmp if ':' in s]
        # Add key/value pairs to the details variable and return dict
        details.update({key.strip(): value.strip() for (key, value) in tmp})
    
    return details
    
def get_disks():
    disks = []
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('list disk\n')
    
    try:
        # Run script
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        # Append disk numbers
        for tmp in re.findall(r'Disk (\d+)\s+\w+\s+(\d+\s+\w+)', output):
            num = tmp[0]
            size = human_readable_size(tmp[1])
            disks.append({'Number': num, 'Size': size})
    
    return disks

def get_partition_details(disk, partition):
    details = {}
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('select disk {}\n'.format(disk['Number']))
        script.write('select partition {}\n'.format(partition['Number']))
        script.write('detail partition\n')
    
    # Diskpart details
    try:
        # Run script
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        # Get volume letter or RAW status
        tmp = re.search(r'Volume\s+\d+\s+(\w|RAW)\s+', output)
        if tmp:
            if tmp.group(1).upper() == 'RAW':
                details['FileSystem'] = RAW
            else:
                details['Letter'] = tmp.group(1)
        # Remove empty lines from output
        tmp = [s.strip() for s in output.splitlines() if s.strip() != '']
        # Split each line on ':' skipping those without ':'
        tmp = [s.split(':') for s in tmp if ':' in s]
        # Add key/value pairs to the details variable and return dict
        details.update({key.strip(): value.strip() for (key, value) in tmp})
    
    # Get MBR type / GPT GUID for extra details on "Unknown" partitions
    guid = partition_uids.lookup_guid(details['Type'])
    if guid:
        details.update({
            'Description':  guid.get('Description', ''),
            'OS':           guid.get('OS', '')})
    
    if 'Letter' in details:
        # Disk usage
        tmp = shutil.disk_usage('{}:\\'.format(details['Letter']))
        details['Used Space'] = human_readable_size(tmp.used)
        
        # fsutil details
        cmd = [
            'fsutil',
            'fsinfo',
            'volumeinfo',
            '{}:'.format(details['Letter'])
            ]
        try:
            output = run_program(cmd)
            output = output.stdout.decode().strip()
        except subprocess.CalledProcessError:
            pass
        else:
            # Remove empty lines from output
            tmp = [s.strip() for s in output.splitlines() if s.strip() != '']
            # Add "Feature" lines
            details['File System Features'] = [s.strip() for s in tmp
                if ':' not in s]
            # Split each line on ':' skipping those without ':'
            tmp = [s.split(':') for s in tmp if ':' in s]
            # Add key/value pairs to the details variable and return dict
            details.update({key.strip(): value.strip() for (key, value) in tmp})
        
    # Set Volume Name
    details['Name'] = details.get('Volume Name', '')
    
    # Set FileSystem Type
    if details.get('FileSystem', '') != 'RAW':
        details['FileSystem'] = details.get('File System Name', 'Unknown')
    
    return details

def get_partitions(disk):
    partitions = []
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('select disk {}\n'.format(disk['Number']))
        script.write('list partition\n')
    
    try:
        # Run script
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        # Append partition numbers
        regex = r'Partition\s+(\d+)\s+\w+\s+(\d+\s+\w+)\s+'
        for tmp in re.findall(regex, output, re.IGNORECASE):
            num = tmp[0]
            size = human_readable_size(tmp[1])
            partitions.append({'Number': num, 'Size': size})
    
    return partitions

def get_table_type(disk):
    part_type = 'Unknown'
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('select disk {}\n'.format(disk['Number']))
        script.write('uniqueid disk\n')
    
    try:
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        if REGEX_DISK_GPT.search(output):
            part_type = 'GPT'
        elif REGEX_DISK_MBR.search(output):
            part_type = 'MBR'
        elif REGEX_DISK_RAW.search(output):
            part_type = 'RAW'
        else:
            part_type = 'Unknown'
    
    return part_type

def get_volumes():
    vols = []
    with open(DISKPART_SCRIPT, 'w') as script:
        script.write('list volume\n')
    
    try:
        # Run script
        output = run_program(['diskpart', '/s', DISKPART_SCRIPT])
        output = output.stdout.decode().strip()
    except subprocess.CalledProcessError:
        pass
    else:
        # Append volume numbers
        for tmp in re.findall(r'Volume (\d+)\s+([A-Za-z]?)\s+', output):
            vols.append({'Number': tmp[0], 'Letter': tmp[1]})
    
    return vols

def is_bad_partition(par):
    return 'Letter' not in par or REGEX_BAD_PARTITION.search(par['FileSystem'])

def prep_disk_for_formatting(disk=None):
    disk['Format Warnings'] = '\n'
    width = len(str(len(disk['Partitions'])))
    
    # Bail early
    if disk is None:
        raise Exception('Disk not provided.')

    # Set boot method and partition table type
    disk['Use GPT'] = True
    if (get_boot_mode() == 'UEFI'):
        if (not ask("Setup Windows to use UEFI booting?")):
            disk['Use GPT'] = False
    else:
        if (ask("Setup Windows to use BIOS/Legacy booting?")):
            disk['Use GPT'] = False
    
    # Set Display and Warning Strings
    if len(disk['Partitions']) == 0:
        disk['Format Warnings'] += 'No partitions found\n'
    for partition in disk['Partitions']:
        display = '    Partition {num:>{width}}:\t{size} {fs}'.format(
            num = partition['Number'],
            width = width,
            size = partition['Size'],
            fs = partition['FileSystem'])
        
        if is_bad_partition(partition):
            # Set display string using partition description & OS type
            display += '\t\t{q}{name}{q}\t{desc} ({os})'.format(
                display = display,
                q = '"' if partition['Name'] != '' else '',
                name = partition['Name'],
                desc = partition['Description'],
                os = partition['OS'])
        else:
            # List space used instead of partition description & OS type
            display += ' (Used: {used})\t{q}{name}{q}'.format(
                used = partition['Used Space'],
                q = '"' if partition['Name'] != '' else '',
                name = partition['Name'])
        # For all partitions
        partition['Display String'] = display

def reassign_volume_letter(letter, new_letter='I'):
    if not letter:
        # Ignore
        return None
    try:
        # Run script
        with open(DISKPART_SCRIPT, 'w') as script:
            script.write('select volume {}\n'.format(letter))
            script.write('remove noerr\n')
            script.write('assign letter={}\n'.format(new_letter))
        run_program(['diskpart', '/s', DISKPART_SCRIPT])
    except subprocess.CalledProcessError:
        pass
    else:
        return new_letter

def remove_volume_letters(keep=None):
    if not keep:
        keep = ''
    with open(DISKPART_SCRIPT, 'w') as script:
        for vol in get_volumes():
            if vol['Letter'].upper() != keep.upper():
                script.write('select volume {}\n'.format(vol['Number']))
                script.write('remove noerr\n')
    
    # Run script
    try:
        run_program(['diskpart', '/s', DISKPART_SCRIPT])
    except subprocess.CalledProcessError:
        pass

def scan_disks():
    """Get details about the attached disks"""
    disks = get_disks()

    # Get disk details
    for disk in disks:
        # Get partition style
        disk['Table'] = get_table_type(disk)

        # Get disk name/model and physical details
        disk.update(get_disk_details(disk))

        # Get partition info for disk
        disk['Partitions'] = get_partitions(disk)
        
        for partition in disk['Partitions']:
            # Get partition details
            partition.update(get_partition_details(disk, partition))

    # Done
    return disks

def select_disk(title='Which disk?', disks=[]):
    """Select a disk from the attached disks"""
    # Build menu
    disk_options = []
    for disk in disks:
        display_name = '{Size}\t[{Table}] ({Type}) {Name}'.format(**disk)
        pwidth=len(str(len(disk['Partitions'])))
        for partition in disk['Partitions']:
            # Main text
            p_name = 'Partition {num:>{width}}: {size} ({fs})'.format(
                num = partition['Number'],
                width = pwidth,
                size = partition['Size'],
                fs = partition['FileSystem'])
            if partition['Name']:
                p_name += '\t"{}"'.format(partition['Name'])
            
            # Show unsupported partition(s)
            if is_bad_partition(partition):
                p_display_name = '{YELLOW}{display}{CLEAR}'.format(
                    display=p_name, **COLORS)
            
            display_name += '\n\t\t\t{}'.format(display_name)
        if not disk['Partitions']:
            display_name += '\n\t\t\t{}No partitions found.{}'.format(
                COLORS['YELLOW'], COLORS['CLEAR'])

        disk_options.append({'Name': display_name, 'Disk': disk})
    actions = [
        {'Name': 'Main Menu', 'Letter': 'M'},
        ]

    # Menu loop
    selection = menu_select(
        title = title,
        main_entries = disk_options,
        action_entries = actions)

    if (selection.isnumeric()):
        return disk_options[int(selection)-1]['Disk']
    elif (selection == 'M'):
        raise GeneralAbort

if __name__ == '__main__':
    print("This file is not meant to be called directly.")