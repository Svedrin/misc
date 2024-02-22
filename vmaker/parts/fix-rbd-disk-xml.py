#!/usr/bin/python

# Read a domain's XML definition from stdin, parse its XML, then extend
# the <disk> object to include all Ceph hosts and the <auth> stanza.
#
# Original generated from libvirt:
#
# <domain>
#   <devices>
#     <disk type="network" device="disk">
#       <driver name="qemu" type="raw" cache="writeback" io="threads"/>
#       <source protocol="rbd" name="rbd/vmaker-test-rbd.img">
#         <host name="dev-vh001" port="6789"/>
#       </source>
#       <target dev="vda" bus="virtio"/>
#     </disk>
#   </devices>
# </domain>
#
# We want:
#
# <domain>
#   <devices>
#     <disk type="network" device="disk">
#       <driver name="qemu" type="raw" cache="writeback" io="threads"/>
#       <auth username='libvirt'>
#         <secret type='ceph' uuid='121954cf-84bc-4dee-92f9-59ca3f4668de'/>
#       </auth>
#       <source protocol="rbd" name="rbd/vmaker-test-rbd.img">
#         <host name="dev-vh001" port="6789"/>
#         <host name="dev-vh002" port="6789"/>
#         <host name="dev-vh003" port="6789"/>
#       </source>
#       <target dev="vda" bus="virtio"/>
#     </disk>
#   </devices>
# </domain>
#
# So we need to add the <auth> section and the other hosts. We can get that
# info from the storage pool definition, the pool name has been passed in as $1.

import sys
import xmltodict
import subprocess

def main():
    vm_data = xmltodict.parse(sys.stdin.read())

    proc = subprocess.Popen(["virsh", "pool-dumpxml", sys.argv[1]], stdout=subprocess.PIPE)
    out, _ = proc.communicate()
    if proc.returncode != 0:
        raise SystemError("could not get pool data")
    pool_data = xmltodict.parse(out)

    vm_data["domain"]["devices"]["disk"]["auth"] = pool_data["pool"]["source"]["auth"]
    del vm_data["domain"]["devices"]["disk"]["auth"]["@type"]
    vm_data["domain"]["devices"]["disk"]["auth"]["secret"]["@type"] = "ceph"

    vm_data["domain"]["devices"]["disk"]["source"]["host"] = pool_data["pool"]["source"]["host"]

    print xmltodict.unparse(vm_data, pretty=True, indent='  ')

if __name__ == '__main__':
    sys.exit(main())
