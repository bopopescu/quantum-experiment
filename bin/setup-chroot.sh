#!/bin/bash
TOP=$(git rev-parse --show-toplevel)
CHROOT=${TOP}/chroot/
REVTOP=$(cd ${TOP}/; git show -s --format=%h\ %an\ \<%ae\>:\ %s )
REVEUTESTER=$(cd ${TOP}/eutester/; git show -s --format=%h\ %an\ \<%ae\>:\ %s )
echo -e "Using quantum-experiment at rev:\n\t${REVTOP}"
if [ ! -e ${TOP}/eutester/.gitignore ]; then
  echo Failed to find eutester checkout, updating submodule
  git submodule udpate --init eutester
else
  echo -e "Using eutester at rev:\n\t${REVEUTESTER}"
fi
COMMAND="/bin/bash -i"
if [ -n "$1" ]; then
  COMMAND="$1"
fi

bindDir() {
  D=$1
  sudo mkdir -p ${CHROOT}/root/${D} && 
  sudo mount -o bind ${TOP}/${D} ${CHROOT}/root/${D}
}

sudo mkdir -p ${CHROOT}/proc/ && 
sudo mount -t proc none ${CHROOT}/proc/ &&

sudo mkdir -p ${CHROOT}/dev/pts &&
sudo mount -t devpts devpts ${CHROOT}/dev/pts &&

bindDir eutester &&
bindDir tests &&
bindDir bin &&
bindDir logs &&

sudo -i chroot ${CHROOT}/ ${COMMAND} 

sudo umount ${CHROOT}/proc/
sudo umount ${CHROOT}/dev/pts
sudo umount ${CHROOT}/root/eutester
sudo umount ${CHROOT}/root/tests
