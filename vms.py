__author__ = 'rephilip'

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from core import get_vmware
from core import get_obj

def get_vm_by_ip(ip):
    si = get_vmware()
    # http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
    search_index = si.content.searchIndex
    vm = search_index.FindByIp(None, ip, True)

    print_vm_details(vm)

    return vm

def get_vm_by_uuid(uuid):
    si = get_vmware()
    # http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
    search_index = si.content.searchIndex
    vm = search_index.FindByUuid(None, uuid, True, True)

    print_vm_details(vm)

    return vm

def get_vm_by_path(path):
    si = get_vmware()
    # http://pubs.vmware.com/vsphere-55/topic/com.vmware.wssdk.apiref.doc/vim.SearchIndex.html
    search_index = si.content.searchIndex
    vm = search_index.FindByInventoryPath(path)

    print_vm_details(vm)

    return vm

def print_vm_details(vm):
    summary = vm.summary
    print "Found Virtual Machine..."
    print "Name          : ", summary.config.name
    print "Path          : ", summary.config.vmPathName
    print "Guest         : ", summary.config.guestFullName
    print "Instance UUID : ", summary.config.instanceUuid
    print "Bios UUID     : ", summary.config.uuid

def update_vif_network(vm, vif_list):
    # vif_list format:
    # vif_list = [
    #     dict(
    #         label='Network adapter 9',
    #         network_name='MyNetwork',
    #         dvs=True,
    #         connected=True
    #     ),
    #     dict(
    #         label='Network adapter 10',
    #         network_name='OtherNetwork',
    #         dvs=False,
    #         connected=True
    #     )
    # ]
    device_change = []
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualEthernetCard) and any(v.get('label', None) == device.deviceInfo.label for v in vif_list):
            # Get the current vif from list
            vif = next((vif for vif in vif_list if vif['label'] == device.deviceInfo.label), None)

            if(vif.get('dvs', None)):
                is_dvs = True
            else:
                is_dvs = False

            if(vif.get('connected', None)):
                connected = vif['connected']
            else:
                connected = device.connectable.connected

            network_name = vif['network_name']

            nicspec = vim.vm.device.VirtualDeviceSpec()
            nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            nicspec.device = device

            # In our case we're always connected to a DVS
            # TODO impact of AVS / NX1KV?
            if is_dvs:
                network = get_obj([vim.dvs.DistributedVirtualPortgroup],
                                  network_name)
                if not isinstance(network, vim.dvs.DistributedVirtualPortgroup):
                    print "Error - Network unknown"
                    return -1

                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = network.key
                dvs_port_connection.switchUuid = network.config.distributedVirtualSwitch.uuid
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nicspec.device.backing.port = dvs_port_connection
            else:
                network = get_obj([vim.Network], network_name)
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicspec.device.backing.network = network
                nicspec.device.backing.deviceName = network_name

            nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nicspec.device.connectable.startConnected = True
            nicspec.device.connectable.allowGuestControl = True
            nicspec.device.connectable.connected = connected
            device_change.append(nicspec)

    if len(device_change) > 0:
        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        try:
            print "Reconfiguring adapter(s) of VM " + vm.summary.config.name + "..."
            vm.ReconfigVM_Task(config_spec)
            return 0;

        except vmodl.MethodFault as error:
            print "Caught vmodl fault : " + error.msg
            return -1
    else:
        print "Nothing to update"
        return -1
