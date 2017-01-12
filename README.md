# README #

VM creator that works purely from bash.

## Prerequisites: ##

*   You're using libvirt to run VMs.

*   apt-get install libvirt-bin libguestfs-tools debootstrap virtinst python-xmltodict

*   If you're intending to use a Ceph pool to store your images, the pool needs to be configured as a libvirt storage pool (*and* it needs to be running).


## Features: ##

*   VM images have a size of 15GB, partitioned using LVM.

    * 5GB root fs (ext4)
    * 2GB /var/log (ext4)
    * 8GB unassigned -- create your data LVs here.

*   Supports Debian Jessie and Ubuntu Xenial.

*   Defaults to building Debian guests when run on Debian and Ubuntu guest when run on Ubuntu.

*   Builds strictly use debootstrap. No golden images or iso installations needed.

*   While building, the image is strictly isolated from the host through libguestfs. That means, it will never ever ever
    show up in your host system as a loop device or through device mapper. Everything works through a single FUSE mount.

*   VMs are self-contained and fully equipped with a boot loader. No host kernel booting needed.

*   The initial debootstrap archive is cached by default and *not* downloaded every time.


*   The target VM image can reside in a Ceph pool.

*   VMs can be automatically registered with libvirt. In that case, they're also automatically started.

*   Network configuration is handled through a bash function that you can override in the settings. The function will
    receive the IP address passed in the *-i* argument and then return gateway, netmask and DNS settings accordingly.

*   Keyboard layout is de with nodeadkeys. (Non-overrideable, but I'll accept pull requests in that direction.)

*   Ubuntu's insane 5 minute boot delay when no network is available is reconfigured to 10 seconds.

*   The Puppet agent can automatically be included in the image and started on first boot. That way, you can easily
    provision the VM after vmaker is done with the initial setup.

*   VMs can also be automatically registered with Pacemaker.


## Usage examples: ##

1.  Build a plain VM image, no registering and/or autobooting, using DHCP for IP:

        ./vmaker.sh -f /var/lib/libvirt/images/shinyvm1.img -n shinyvm1

2.  Build a plain VM image, no registering and/or autobooting, with a static IP:

        ./vmaker.sh -f /var/lib/libvirt/images/shinyvm2.img -n shinyvm2 -i 192.168.0.123

3.  Build a VM image using DHCP for IP and register it with libvirt:

        ./vmaker.sh -f /var/lib/libvirt/images/shinyvm3.img -n shinyvm3 --virt-install

4.  Build a VM image with puppet using DHCP for IP and register it with libvirt:

        ./vmaker.sh -f /var/lib/libvirt/images/shinyvm4.img -n shinyvm4 --puppet --virt-install

5.  Build a VM image stored in a Ceph pool with a static IP and register it with libvirt:

        root@pevh010:~/vmaker# virsh pool-dumpxml peha
        <pool type='rbd'>
          <name>peha</name>
          <uuid>4726bc33-5f60-4813-b965-051562f5f54d</uuid>
          <capacity unit='bytes'>3297748451328</capacity>
          <allocation unit='bytes'>180128346714</allocation>
          <available unit='bytes'>1956380938240</available>
          <source>
            <host name='192.168.142.101' port='6789'/>
            <host name='192.168.142.102' port='6789'/>
            <host name='192.168.142.103' port='6789'/>
            <name>peha</name>
            <auth type='ceph' username='libvirt'>
              <secret uuid='121954cf-84bc-4dee-92f9-59ca3f4668de'/>
            </auth>
          </source>
        </pool>

        root@pevh010:~/vmaker# ./vmaker.sh -f rbd:peha/peha070-n1.img -n peha070-n1 -i 10.10.5.59 --puppet --virt-install


## Example settings for multiple networks: ##

This is a `settings.sh` example for when you need to support multiple target networks with different settings:

    get_network () {
        echo "NETWORK_METHOD=static"
        echo "NETWORK_IPADDR=$IPADDR"

        echo 'NETWORK_NAMESERVERS="192.168.0.1"'
        echo "NETWORK_DOMAIN=local.lan"
        echo "NETWORK_NETMASK=24"

        if [ "`echo $IPADDR | cut -d. -f1-3`" = 192.168.0 ]; then
            BRIDGE=haus0
            GATEWAY=192.168.0.1
        elif [ "`echo $IPADDR | cut -d. -f1-3`" = 10.5.0 ]; then
            BRIDGE=svdr0
            GATEWAY=10.5.0.1
        fi

        echo "NETWORK_BRIDGE=$BRIDGE"
        echo "NETWORK_GATEWAY=$GATEWAY"
    }

This way, the bridge and gateway will be adapted automatically according to the IP the VM is configured with.


## Known bugs and limitations: ##

*   Only tested thoroughly with Ubuntu. I (sadly) use the Debian version less regularly.

*   Only one build can run at a time because the guest is always mounted to */mnt*. (That also means that nothing *else* may be mounted at */mnt* during that time.)

*   Network config adaptation only works with static IPs (there's no --network option, so the IP is the only thing you can pass in).
