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
  COMMAND="/bin/bash -i -c \"$@\""
fi
echo -e "Using command: ${COMMAND}"

bindDir() {
  D=$1
  sudo mkdir -p ${CHROOT}/root/${D} && 
  sudo mount -o bind ${TOP}/${D} ${CHROOT}/root/${D}
}

sudo mkdir -p ${CHROOT}/proc/ && 
sudo mount -t proc none ${CHROOT}/proc/ &&

#sudo mkdir -p ${CHROOT}/dev/pts &&
#sudo mount -t devpts devpts ${CHROOT}/dev/pts &&

sudo mount -o bind /dev chroot/dev &&

bindDir eutester &&
bindDir tests &&
bindDir bin &&
bindDir logs &&

sudo -i chroot ${CHROOT}/ ${COMMAND}

mount | awk '/quantum/{print $3}' | xargs -i sudo umount {}
