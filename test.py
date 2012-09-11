#!/usr/bin/python
from eucaops import Eucaops
from eutester import eutestcase.EutesterTestcase

class MyFirstTest(EutesterTestcase):

    def setUp(self):
        """
        Pass in the appropriate config file with at least lines describing machines in the Eucalyptus Deployment
        192.168.51.11	CENTOS	5.8	64	REPO	[CC00 CLC SC00 WS]
        192.168.51.13	CENTOS	5.8	64	REPO	[NC00]
        """ 
        self.tester = Eucaops(config_file="/root/cloud.conf", password="foobar")
        self.keypair = self.tester.add_keypair()
        self.group = self.tester.add_group()
        self.tester.authorize_group(self.group)
        self.tester.authorize_group(self.group, port=-1, protocol="icmp")
        self.reservation = None

    def testInstance(self):
        image = self.tester.get_emi(root_device_type="instance-store")
        ### 1) Run an instance
        try:
            self.reservation = self.tester.run_instance(image, self.keypair.name, self.group.name)
        except Exception, e:
            self.fail("Caught an exception when running the instance: " + str(e))
        for instance in self.reservation.instances:
            ### 2) Ping the instance
            ping_result = self.tester.ping(instance.public_dns_name)
            self.assertTrue(ping_result, "Ping to instance failed")
            ### 3) Run command on instance
            uname_result = instance.sys("uname -r")
            self.assertNotEqual(len(uname_result), 0, "uname failed")

    def tearDown(self):
        if self.reservation is not None:
            self.tester.terminate_instances(self.reservation)
        self.tester.delete_keypair(self.keypair)
        self.tester.local("rm " + self.keypair.name + ".pem")
        self.tester.delete_group(self.group)
