from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import os

_vcenter_host = os.environ.get("VCENTER_HOSTNAME", None)
_vcenter_username = os.environ.get("VCENTER_USERNAME", None)
_vcenter_password = os.environ.get("VCENTER_PASSWORD", None)
_vmware = None

def vmware_logout():
    global _vmware
    if _vmware:
        _vmware.Disconnect()

def get_vmware():
    """
    Create or Maintain VMware session
    """
    global _vmware

    if not _vmware:
        _vmware = SmartConnect(host=_vcenter_host,
                               user=_vcenter_username,
                               pwd=_vcenter_password,
                               port=int(443))

    return _vmware

def get_obj(vimtype, name):
    """
     Get the vsphere object associated with a given text name
    """
    si = get_vmware()
    content = si.RetrieveContent()
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype, True)
    for view in container.view:
        if view.name == name:
            obj = view
            break
    return obj
