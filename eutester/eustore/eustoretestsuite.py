'''
Created on Apr 13, 2012

@author: clarkmatthew

#note:
currently the test wrappers assume eucarc in the users home dir 

example:
from eustoretests import Eustoretests
et = Eustoretests(config_file="2b_tested.lst", password="foobar")
list = et.get_uninstalled_summary()
et.install_all_images(list=list)

     eustore-install-image -h 
          -h, --help            show this help message and exit
          -i IMAGE_NAME, --image_name=IMAGE_NAME
                                name of image to install
          -t TARBALL, --tarball=TARBALL
                                name local image tarball to install from
          -s DESCRIPTION, --description=DESCRIPTION
                                description of image, mostly used with -t option
          -a ARCHITECTURE, --architecture=ARCHITECTURE
                                i386 or x86_64, mostly used with -t option
          -p PREFIX, --prefix=PREFIX
                                prefix to use when naming the image, mostly used with
                                -t option
          -b BUCKET, --bucket=BUCKET
                                specify the bucket to store the images in
          -k KERNEL_TYPE, --kernel_type=KERNEL_TYPE
                                specify the type you're using [xen|kvm]
          -d DIR, --dir=DIR     specify a temporary directory for large files
          --kernel=KERNEL       Override bundled kernel with one already installed
          --ramdisk=RAMDISK     Override bundled ramdisk with one already installed
          
          Standard Options:
            -D, --debug         Turn on all debugging output
            --debugger          Enable interactive debugger on error
            -U URL, --url=URL   Override service URL with value provided
            --region=REGION     Name of the region to connect to
            -I ACCESS_KEY_ID, --access-key-id=ACCESS_KEY_ID
                                Override access key value
            -S SECRET_KEY, --secret-key=SECRET_KEY
                                Override secret key value
            --version           Display version string
      
'''

from eucaops import Eucaops
from eutester import euinstance, euvolume
import logging
from boto.ec2.snapshot import Snapshot
import re
import time
import unittest
import inspect
import gc
import sys
import os
#import httplib


class User():
    name = ""
    uid = ""
    group= ""
    udir = ""
    
    def __init__(self,name="",uid="",group="",udir=""):
        self.name = name
        self.id = uid
        self.group = group
        self.dir = udir
        self.__name__ = name
        self.__str__ = name
        

class TestStatus():
    not_run = "not run"
    success = "SUCCESS"
    failed = "FAILED"
    
class ImageIndex():
    '''
                id          distro      arch      date      ver      rev    size    user       kerneltype            ----           id2            id3            type          email    
           ['4150406313', 'centos', 'i386', '2011.07.02', 'CentOS', '5', '1.3GB', 'root,', 'Hypervisor-Specific', 'Kernels', '20110716161844', '6e69-7565', 'centos-based', 'images@lists.eucalyptus.com']
    '''
    id = 0   
    distro =1
    arch = 2
    date = 3
    ver = 4
    rev = 5
    size = 6
    user = 7 
    kerneltype = 8 
    #junk = 9
    id2 = 10
    id3 = 11
    type = 12
    email = 13
    
class EustoreTests():
    install_test = "install_test"
    running_test = "running_test"
    metadata_test = "metadata_test"
    user_test = "user_test"
    root_test = "root_test"
    volume_test = "volume_test"
    reboot_test = "reboot_test"
    terminate_test = "terminate_test"

class EustoreImage():
    
    def __init__(self, 
                id = "",
                distro = "",
                arch = "",
                date = "",
                ver = "",
                rev = "",
                size = 0,
                user = "",
                kerneltype = "", 
                id2 = "",
                id3 = "",
                type = "",
                email = "",
                emi = '', 
                eki = '',
                eri = '',
                remotestring = '',
                logdir='../artifacts/'):
        
        self.id = id   
        self.distro = distro
        self.arch = arch
        self.date = date
        self.ver = ver
        self.rev = rev
        self.size = float(size)
        self.user = user
        self.kerneltype = kerneltype 
        self.id2 = id2
        self.id3 = id3
        self.type = type
        self.email = email
        self.emi = emi
        self.eki = eki
        self.eri = eri
        self.remotestring = remotestring
        self.reservation = []
        self.name = id+"_"+ver+"_"+rev+"_"+arch  
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        self.logger = logging.getLogger(self.name)
        hdlr = logging.FileHandler(logdir+self.name+".log")
        formatter = logging.Formatter('%(asctime)s:[%(funcName)s()]:[%(lineno)d]:['+str(self.name)+']: %(message)s')
        hdlr.setFormatter(formatter)
        self.logger.addHandler(hdlr)
        self.logger.setLevel(logging.DEBUG)
        #self.debug = self.logger.debug
        self.results = { 
                EustoreTests.install_test : TestStatus.not_run,
                EustoreTests.running_test : TestStatus.not_run,
                EustoreTests.metadata_test: TestStatus.not_run,
                EustoreTests.user_test : TestStatus.not_run,
                EustoreTests.root_test : TestStatus.not_run,
                EustoreTests.volume_test :TestStatus.not_run,
                EustoreTests.reboot_test : TestStatus.not_run,
                EustoreTests.terminate_test :  TestStatus.not_run
               }
        self.debug("######################START#############################", verbose = False)
 
    def debug(self, msg, verbose=True):
        if verbose:
            print msg
        self.logger.debug(msg)
    
    def printdata(self,printmethod=None):
        if printmethod is None:
            printmethod = self.debug
        printmethod("\n------------------"+str(self.name)+"----------------------")
        for key in self.__dict__:
            value = self.__dict__[key]
            if ( isinstance(value, basestring) or isinstance(value,int) ):
                printmethod( str(key)+ " = " + str(value))
        self.printresults(printmethod=printmethod)
        
    def printresults(self,printmethod = None):
        if printmethod is None:
            printmethod = self.debug
        for test in self.results:
            printmethod( str("TEST:"+str(test)).ljust(25)+str(" RESULT:"+self.results[test]).ljust(0))
        

class Eustoretestsuite():
    acceptable_users=["eucalyptus"]
    cur_image = None
    
    
    def __init__(self, tester=None,  config_file='../input/2b_tested.lst', password="foobar",url=None, list=None, volumes=None, keypair=None, group=None, image=None, zone='PARTI00',  eof=1):
        if tester is None:
            self.tester = Eucaops( config_file=config_file, password = password)
            self.tester.exit_on_fail = eof
        else:
            self.tester = tester
            self.tester.exit_on_fail = eof
        self.zone = zone
        self.url = url
        self.url_export_string = str(" ")
        if self.url is not None:
            self.url_export_string = "export EUSTORE_URL="+str(self.url)+" &> /dev/null &&"
        if list is None:
            self.list = self.get_eustore_images()
        else:
            self.list = list
        self.group = self.get_a_group()
        self.keypair = self.get_a_key()
        self.sync_installed_list()
        
            
            
    def get_a_key(self):    
        keypair = None
        keys = self.tester.get_all_current_local_keys()
        if keys != []:
            keypair = keys[0]
        if keypair is None:
            try:
                keypair = self.tester.add_keypair("eustoretest" + "-" + str(time.time()))
            except Exception, e:
                raise Exception("Error when adding keypair. Error:"+str(e))
        return keypair
            
    def get_a_group(self, group_name="eustoregroup"):
        try:
            group = self.tester.add_group(group_name)
            self.tester.authorize_group_by_name(group.name)
            self.tester.authorize_group_by_name(group.name,protocol="icmp",port=-1)
        except Exception, e:    
            raise Exception("Error when setting up group:"+str(group_name)+", Error:"+str(e))
        return group
              
    def debug(self,msg):
        if self.cur_image is not None:
            self.cur_image.debug(msg)
        return self.tester.debug(msg)
    
    
    
    def get_eustore_images(self):
        '''
        Attempts to populate a list of images by retrieving image attributes from eustore command(s).   
        '''
        ii = ImageIndex()
        images = []
        out = self.tester.sys( self.url_export_string+" eustore-describe-images -v")
        l = 0
        while (l < len(out)):
            line = out[l].strip().split()+out[l+1].strip().split()
            image = EustoreImage(
                                id = line[ii.id],
                                distro = line[ii.distro],
                                arch = line[ii.arch],
                                date = line[ii.date],
                                ver = line[ii.ver],
                                rev = line[ii.rev],
                                size = float(re.sub("GB","", line[ii.size])),
                                user = line[ii.user],
                                kerneltype = line[ii.kerneltype], 
                                id2 = line[ii.id2],
                                id3 = line[ii.id3],
                                type = line[ii.type],
                                email = line[ii.email],
                                remotestring = out[l].strip()+out[l+1].strip()
                                )
            images.append(image)
            l += 2
        return images
            
            
    def get_system_images(self, emi=None, root_device_type=None, root_device_name=None, location=None, state="available", arch=None, owner_id=None):
        """
        Get images matching the provided criteria. 
        By default matches image location containing the  string held by the 'location' option.
        emi              (optional string ) Partial ID of the emi to return, defaults to the 'emi-" prefix to grab any
        root_device_type (optional string)  example: 'instance-store' or 'ebs'
        root_device_name (optional string)  example: '/dev/sdb' 
        location         (optional string)  partial on location match example: 'centos'
        state            (optional string)  example: 'available'
        arch             (optional string)  example: 'x86_64'
        owner_id         (optional string) owners numeric id
        """
        retlist = []    
        images = self.tester.ec2.get_all_images()
        for image in images:
            
            if (emi is not None) and (not re.search(emi, image.id)):      
                continue  
            if ((root_device_type is not None) and (image.root_device_type != root_device_type)):
                continue            
            if ((root_device_name is not None) and (image.root_device_name != root_device_name)):
                continue       
            if ((state is not None) and (image.state != state)):
                continue            
            if ((location is not None) and (not re.search( location, image.location))):
                continue           
            if ((arch is not None) and (image.architecture != arch)):
                continue                
            if ((owner_id is not None) and (image.owner_id != owner_id)):
                continue
            
            retlist.append(image)
        return retlist
            
            
            
    def get_registered_emi(self, eustore_image,  emi="emi-"):
        images = self.get_system_images(emi, location=eustore_image.id)    
        if images == []:
            return None
        else:
            return images
    
    def get_registered_eki(self, eustore_image):
        return self.get_registered_emi(eustore_image, emi="eki-")
    
    def get_registered_eri(self, eustore_image):
        return self.get_registered_emi(eustore_image, emi="eri-")
    
        
   
            
    def install_image(self,eustore_image,
                      help=False,
                      tarball=None,
                      description=None,
                      arch=None,
                      prefix=None,
                      bucket=None,
                      kernel_type=None,
                      dir="/disk1/storage",
                      kernel=None,
                      ramdisk=None,
                      url=None,
                      region=None,
                      access_key=None,
                      secret_key=None,
                      force=False, 
                      eucarc=False,
                      xof=False,
                      timepergig=1000):
  

        image = eustore_image
        self.cur_image = image
        cmd = ""
        start = time.time()
        
        #Check to see if image has already been installed
        if (not force) and  (self.get_registered_emi(eustore_image) is not None):
            eustore_image.results[EustoreTests.install_test] = TestStatus.success
            raise Exception('Image:"'+str(image.name)+'" is already installed')
       
        timeout = int(image.size*timepergig)
        print "image.size:"+str(image.size)+" and timepergig:"+str(timepergig)+" = timeout:"+str(timeout)
        
        #Build the eustore command...
        if eucarc:
            cmd = "source eucarc && "
        cmd = cmd + self.url_export_string+" eustore-install-image"+self.get_standard_opts(url=url, region=region, access_key=access_key, secret_key=secret_key)  
        cmd = cmd + " -i "+str(eustore_image.id)
        if help == True:
            cmd = cmd + " -h"
            
        if tarball is not None:
            cmd = cmd + " -t "+ str(tarball)
            
        if description is not None:
            cmd = cmd + " -s "+ str(description)
            
        if arch is not None:
            cmd = cmd + " -a "+ str(arch)
            
        if prefix is not None:
            cmd = cmd + " -p "+ str(prefix)
            
        if kernel_type is not None:
            cmd = cmd + " -k "+ str(kernel_type)
        else:
            kernel_type = ""
            
        if bucket is not None:
            cmd = cmd + " -b "+ str(bucket)
        else:
            cmd = cmd + " -b "+ str(eustore_image.name).lower()+"_"+str(kernel_type)
            
        if dir is not None:
            cmd = cmd + " -d "+ str(dir)
            
        if kernel is not None:
            cmd = cmd + " --kernel="+str(kernel)
            
        if ramdisk is not None:
            cmd = cmd + " --ramdisk="+str(ramdisk)
        
        cmd = cmd + " && echo 'SUCCESS'"
        print "-----------------------------------------------------------------------------------------"
        print "-----------------------------------------------------------------------------------------"
        print " image: "+image.name+"_"+str(kernel_type)
        print "-----------------------------------------------------------------------------------------"
        print "-----------------------------------------------------------------------------------------"
        print "Executing cmd:"+str(cmd)
        try:     
            out = self.tester.sys(cmd, timeout=timeout)
            if re.search("SUCCESS",out[len(out)-1]):
                for line in out:
                    if re.search("Error", line):
                        self.debug("Found Error from cmd:"+str(cmd))
                        raise Exception("Found Error from cmd:"+str(cmd))
            else:
                self.debug("Command exited with err:"+str(cmd))
                raise Exception("Command exited with err:"+str(cmd))
            
            
            #Now verify the appropriate images were actually installed on the system
            emi = self.get_registered_emi(eustore_image)[0]
            if (emi is None):
                self.debug('Image:"'+str(image.name)+'" is not found on system after install')
                raise Exception('Image:"'+str(image.name)+'" is not found on system after install')
            
            #Get the associated eki and eri
            eki_id = emi.kernel_id
            eri_id = emi.ramdisk_id
            
            #Verify the appropriate EKI was installed and associated with this EMI
            if (kernel is not None): 
                if(kernel != eki_id):
                    self.debug("Kernel specified does not match specified EKI. EMI:"+str(emi.id)+" Image:"+str(image.name))
                    raise Exception("Kernel specified does not match specified EKI. EMI:"+str(emi.id)+" Image:"+str(image.name)) 
            else:
                eki = self.get_registered_eki(eustore_image)
                if eki is None:
                    self.debug('EKI for Image:"'+str(image.name)+'" is not found on system after install')
                    raise Exception('EKI for Image:"'+str(image.name)+'" is not found on system after install')
                else:
                    if (eki.id != eki_id):
                        self.debug("Kernel specified does not match associated EKI. EMI:"+str(emi.id)+" Image:"+str(image.name))
                        raise Exception("Kernel specified does not match associated EKI. EMI:"+str(emi.id)+" Image:"+str(image.name))
                    
            #Verify the appropriate ERI was installed and associated with this EMI        
            if (ramdisk is not None):
                if (ramdisk != eri_id):
                    self.debug("Ramdisk specified does not match associated ERI. EMI:"+str(emi.id)+" Image:"+str(image.name))
                    raise Exception("Ramdisk specified does not match associated ERI. EMI:"+str(emi.id)+" Image:"+str(image.name))
            else:
                eri = self.get_registered_eri(eustore_image)
                if eri is None:
                    self.debug('ERI for Image:"'+str(image.name)+'" is not found on system after install')
                    raise Exception('ERI for Image:"'+str(image.name)+'" is not found on system after install')
                else:
                    if (eri.id != eri_id):
                        self.debug("Ramdisk specified does not match associated ERI. EMI:"+str(emi.id)+" Image:"+str(image.name))
                        raise Exception("Ramdisk specified does not match associated ERI. EMI:"+str(emi.id)+" Image:"+str(image.name))
            image.emi = emi.id
            image.eri = eri_id
            image.eki = eki_id
            
            eustore_image.results[EustoreTests.install_test] = TestStatus.success
            self.debug(cmd+" Succeeded")  
        except Exception, e:
            eustore_image.results[EustoreTests.install_test] = TestStatus.failed
            self.debug("Image:"+image.name+" failed to install, err:"+str(e))
            if xof:
                raise Exception("Image:"+image.name+" failed to install, err:"+str(e))
        
        finally:
            elapsed = int(time.time()-start)
            self.debug("Command finish in: "+str(elapsed)+" seconds")
            self.cur_image = None
        
    
            
    def get_standard_opts(self,url=None,region=None,access_key=None,secret_key=None):    
            ret = ""
            if region is not None:
                ret = ret+"--region="+str(region)+" "  
            if access_key is not None:
                ret = ret+"-I "+str(access_key)+" "
            if secret_key is not None:   
                ret = ret+"-S "+str(secret_key)+" "
            return ret
        
    
    def get_eustore_image_by_string(self, searchstring, list=None):

        retlist = []
        if list is None:
            list = self.list
        for image in list: 
            if re.search(searchstring, image.remotestring):
                retlist.append(image)
        return retlist
        
    
    def install_all_images(self, hyper="both",eucarc=True, searchstring=None, imglist = None, force=False):
        '''
        Attempts to install all images either in self.list or the provided imglist. 
        By default will install both xen and kvm images, but this can be limited by use of the hyper var.
        Options:
        hyper -optional string - kvm, xen, both. Used to determine which image to use for installation
        eucarc - optional- used to determine whether or not the command should source the eucarc or specify args instead
        searchstring - optional-  will only install images whos remote string matches the given string
        imglist -optional - defaults to self.list, list used to gather all images to be installed
        force - optional - if True, will attempt to install if existing image is detected. Otherwise will skip installed images.
        '''
        if imglist is None:
            imglist = self.list
        if searchstring is not None:
            imglist = self.get_eustore_image_by_string(searchstring, list=imglist)
        for image in imglist:
            try: 
                if (image.kerneltype == "Single"):
                    self.debug("Installing image:"+image.name+" kernel_type:"+image.kerneltype+" , HYPER:NONE")
                    self.install_image(image, eucarc=eucarc)
                else:
                    if (hyper == "both" ) or (hyper == "xen"):
                        self.debug("Installing image:"+image.name+" kernel_type:"+image.kerneltype+" HYPER:XEN")
                        self.install_image(image, eucarc=True, kernel_type="xen")
                    if (hyper == "both ") or (hyper == "kvm"):
                        self.debug("Installing image:"+image.name+" kernel_type:"+image.kerneltype+" HYPER:KVM")
                        self.install_image(image, eucarc=True, kernel_type="kvm")      
            except Exception, ie:
                self.debug("Image;"+image.name+" failed."+str(ie))
                pass
    
    def get_eustore_image_by_id(self, emi_id=None, eri_id=None, eki_id=None):
        
        for image in self.list:
            if (emi_id is not None) and (not re.search(emi_id, image.emi)):      
                continue  
            if (eki_id is not None) and (not re.search(eki_id, image.eki)):      
                continue
            if (eri_id is not None) and (not re.search(eri_id, image.eri)):      
                continue
            self.debug("get_eustore_image_by_id,emi_id="+str(emi_id)+" = "+str(image.name))
            return image
        return None
        
        
        
    def sync_installed_list(self, updateimage=True):
        '''
        Attempts to get a diff of images in our list vs what the system is reporting. 
        This relies upon the bucket location having the image id text in it. 
        Returns a list of images found in our eustore list that are not believed 
        to be installed on the system. Can be later passed to install_all_images, etc..
        '''
        retlist = []
        for image in self.list:
            self.debug("Checking to see if image:"+str(image.name)+" is installed")
            emis = self.get_registered_emi(image)
            if emis is None:
                self.debug("Image: "+str(image.name)+" not found on system")
                retlist.append(image)
            else:
                emi = emis[0]
                self.debug("Image: "+str(image.name)+" found installed on system")
                if updateimage:
                    #Get the associated eki and eri
                    image.eki = emi.kernel_id
                    image.eri = emi.ramdisk_id
                    image.emi = emi.id
                    image.results[EustoreTests.install_test]=TestStatus.success
        return retlist
    
    def print_image_list(self,list=None, verbose=False):
        if list is None:
            list = self.list
            for image in list:
                self.debug("IMAGE: "+str(image.name)+" Install Status: "+str(image.results[EustoreTests.install_test]))
                if verbose:
                    image.printdata()
    def test_image_list(self, image_list=None,  zone=None):
        if image_list is None:
            image_list = self.list
        if zone is None:
            zone = self.zone    
        for image in image_list:
            try:
                self.run_image_test_suite(image, zone=zone)
                time.sleep(10)
            except Exception, e:
                self.debug("Caught Exception while running image test for:"+str(image.name)+", err:"+str(e))
                pass
            

            
                
                
    def run_image_test_suite(self,image, vmtype=None, zone='PARTI00', xof=False):  
        '''
        Runs a set of tests against an image, starts by running an euinstance of an image. If the image continues
        to running the remaining tests are ran against the image. Logging/results/debugging messages should be printed to the
        image specific dir/file. usually ../artifacts/*imagename*.log
        
        '''
        self.cur_image = image #set logger for this image    
        failcode = 0 
        try:
            #first try to run the image, exit if this fails as there's no point in running the remaining tests
            try:
                res = self.run_image(image, vmtype=vmtype, zone=zone)
                inst = res.instances[0]
            except Exception, re:
                image.results[EustoreTests.running_test] = TestStatus.failed
                self.debug("("+str(image.name)+") error:"+str(re))
                raise re
          
            #Perform tests on the running instance, continue on failure for these tests
            try:
                self.instance_metadata_test(inst)
                self.debug("SUCCESS - METADATA TEST - ("+str(image.name)+")")
            except Exception, e:
                self.debug("!!!!!! FAILED - METADATA TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            try:
                self.instance_root_test(inst)
                self.debug("SUCCESS - ROOT TEST - ("+str(image.name)+")")
            except Exception, e:
                self.debug("!!!!!! FAILED - ROOT TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            try:
                self.instance_users_test(inst)
                self.debug("SUCCESS - USERS TEST - ("+str(image.name)+")")
            except Exception, e:
                self.debug("!!!!!! FAILED - USERS TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            try:    
                self.instance_attach_vol_test(inst,volcount=2)
                self.debug("SUCCESS - ATTACH VOLUMES TEST - ("+str(image.name)+")")
            except Exception, e:
                self.debug("!!!!!! FAILED - ATTACH VOLUME TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            try:
                self.instance_reboot_test(inst)
                self.debug("SUCCESS - REBOOT TEST - ("+str(image.name)+")")
            except Exception, e:
                self.debug("!!!!!! FAILED - REBOOT TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            try:
                self.instance_terminate_test(res)
                self.debug("SUCCESS - TERMINATE TEST - ("+str(image.name)+")")
            except Exception, e: 
                self.debug("!!!!!! FAILED -  TEST - ("+str(image.name)+") error:"+str(e))
                failcode = 1 
                pass
            
            
        except Exception, e:
            self.debug("!!!!!! FAILED  - ("+str(image.name)+") error:"+str(e))
            failcode = 1
            raise e
        finally:
            self.clean_up_running_instances_for_image(image)
            self.debug(str('FAIL' if failcode == 1 else "SUCCESS")+" IMAGE:"+str(image.name))
            image.printdata(printmethod=self.debug)
            self.cur_image = None
            return failcode
            
    def clean_up_running_instances_for_image(self,image, timeout=300):
        self.debug("clean_up_running_instance_for_image: "+str(image.name))
        failstr=''
        emis = self.get_registered_emi(image)
        if emis != []:
            emi = emis[0]
            for instance in self.tester.get_instances(image_id=emi.id):
                try:
                    if (instance.state != 'terminated'):
                        self.debug("Found Instance to terminate:"+str(instance.id))
                        instance.terminate()
                        self.tester.wait_for_instance(instance, state='terminated')
                    self.debug("Instance:"+str(instance.id)+" terminated")
                except Exception, e:
                    failstr = failstr+ "instance:"+instance.id+"Failed:"+str(e)+"\n"
                    pass
        else:
            self.debug("No instances found to clean up")
        if failstr != '':
            raise Exception("Failed to terminated instances:"+str(failstr))
        
                
            
    def run_image(self,image, vmtype=None, zone='PARTI00'):
        if vmtype is None:
            if image.size <= 2:
                vmtype = 'c1.medium'
            elif image.size <= 5:
                vmtype = 'm1.large'
            else:
                vmtype = 'm1.xlarge'
        self.debug("#####STARTING run_image test########")
        image.results[EustoreTests.running_test] = TestStatus.failed
        try:
            emi = self.get_registered_emi(image)[0]
        except Exception, e:
            raise Exception("Could not get registered EMI for image:"+str(image.name)+" err:"+str(e))
        
        self.debug("Running image:"+str(image.name)+", vmtype:"+str(vmtype)+" keypair:"+str(self.keypair.name)+" group:"+str(self.group)+" zone:"+str(zone))
        res = self.tester.run_instance(image=emi, keypair=self.keypair.name, group=self.group, type=vmtype, zone=zone)
        if res == []:          
            raise Exception("Reservation was empty, failed to run: "+str(image.name))      
        image.results[EustoreTests.running_test] = TestStatus.success
        return res
        
            
    def instance_metadata_test(self,inst):
        self.debug("#######STARTING instance_metadata_test##########")
        image = self.get_eustore_image_by_id(emi_id=inst.image_id)
        image.results[EustoreTests.metadata_test] = TestStatus.failed
        if inst.get_metadata('instance-id')[0] != inst.id:
            raise Exception("("+str(image.name)+") Metadata test failed")
        image.results[EustoreTests.metadata_test] = TestStatus.success
        
    
    def instance_attach_vol_test(self,inst, volcount=1):
        self.debug("###########STARTING instance_attach_vol_test##########")
        image = self.get_eustore_image_by_id(emi_id=inst.image_id)
        image.results[EustoreTests.volume_test] = TestStatus.failed
        zone = inst.placement
        try:
            for i in xrange(0,volcount):
                try:
                    vol = self.tester.get_volume(status='available', zone=zone, maxsize=1)
                except Exception, e:
                    self.debug("Err trying to get an existing volume, making new one... err:"+str(e))
                    vol = self.tester.create_volume(zone)
                    pass
                inst.attach_volume(vol)
        except Exception, ae:
            raise Exception("("+str(image.name)+") Failed to attach volume to:"+str(inst.id)+"err:"+str(e))
        image.results[EustoreTests.volume_test] = TestStatus.success
        
        
    def instance_reboot_test(self,inst, checkvolstatus=True):
        self.debug("############STARTING instance_reboot_test#############")
        image = self.get_eustore_image_by_id(emi_id=inst.image_id)
        image.results[EustoreTests.reboot_test] = TestStatus.failed
        try:
            inst.reboot_instance_and_verify(checkvolstatus=checkvolstatus)
            image.results[EustoreTests.reboot_test] = TestStatus.success
        except Exception, e:
            image.results[EustoreTests.reboot_test] = TestStatus.failed
            raise Exception("("+str(image.name)+")Failed instance_reboot_test, err:"+str(e))
        
        
    def instance_users_test(self, inst, userlist=[]):
        self.debug("############STARTING instance_users_test#################")
        image = self.get_eustore_image_by_id(emi_id=inst.image_id)
        image.results[EustoreTests.user_test] = TestStatus.failed
        users = inst.get_users() 
        if users != userlist:
            raise Exception("("+str(image.name)+")Image has unknown Non-system users: "+"".join(users))
        image.results[EustoreTests.user_test] = TestStatus.success
        
    def instance_root_test(self, inst, password = None):
        self.debug("############STARTING isntance_root_test################")
        image = self.get_eustore_image_by_id(emi_id=inst.image_id)
        if inst.get_user_password('root') != password:
            image.results[EustoreTests.root_test] = TestStatus.failed
            raise Exception("("+str(image.name)+")root user has bad password!")
        image.results[EustoreTests.root_test] = TestStatus.success
        
    def instance_terminate_test(self,res):
        self.debug("#######STARTING instance_terminate_test##########")
        try:
            inst = res.instances[0]
            image = self.get_eustore_image_by_id(emi_id=inst.image_id)
            image.results[EustoreTests.terminate_test] = TestStatus.failed
            self.tester.terminate_instances(res)
            image.results[EustoreTests.terminate_test] = TestStatus.success
        except Exception, e:
            self.debug("Trying single Termination, Problem with terminating reservation:" +str(e))
            try:
                self.clean_up_running_instances_for_image(image)
                image.results[EustoreTests.terminate_test] = TestStatus.success
            except Exception, se:
                self.debug("Failed single termination for image:"+str(image.name))
                raise se
                

    def get_images_by_test_result(self,list=None, eustoretest=None,result=TestStatus.failed ):
        """ 
        Attempts to return a subset list of images who's test results match the result give. 
        By default this will traverse each image in self.list, will then traverse the image.results list for each
        EustoreTest matching TestStatus.failed.
        """
        retlist = []
        if list is None:
            list = self.list
        
        if eustoretest is None:
            #return all images who have any test which results matches 'result'
            for image in list:
                for test in image.results:
                    if image.results[test] == result:
                        retlist.append(image)
            return retlist
        else:
            #return any images whos specific eustore test mataches 'result'
            for image in list:
                try:
                    t = EustoreTests.__dict__[eustoretest]
                except Exception, te:
                    raise Exception("get_images_by_test_result, provided invalid test type:"+str(eustoretest)+", err;"+str(te))
                if image.results[t] == result:
                    retlist.append(image)
            return retlist
        
                            
                
    
    
    def print_image_list_results(self,list=None):
        if list is None:
            list = self.list
        for image in list:
            self.cur_image = image
            image.printdata()
            self.cur_image = None
        
    
            
            
            