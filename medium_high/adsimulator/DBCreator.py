# Requirements - pip install neo4j-driver
# This script is used to create randomized sample databases.
# Commands
# 	dbconfig - Set the credentials and URL for the database you're connecting too
#	connect - Connects to the database using supplied credentials
# 	setparams - Set the settings JSON file
# 	setdomain - Set the domain name
# 	cleardb - Clears the database and sets the schema properly
#	generate - Connects to the database, clears the DB, sets the schema, and generates random data

from neo4j import GraphDatabase
import cmd
import math
from collections import defaultdict
import uuid
import time
import random
import os
from adsimulator.generators.groups import generate_default_groups
from adsimulator.generators.domains import generate_domain, generate_trusts
from adsimulator.generators.gpos import generate_default_gpos, link_default_gpos, generate_gpos, link_gpos_to_ous,\
    gplink_domain_to_ous
from adsimulator.generators.ous import generate_domain_controllers_ou, generate_computer_ous, generate_user_ous, link_ous_to_domain
from adsimulator.generators.acls import generate_enterprise_admins_acls, generate_administrators_acls, generate_domain_admins_acls,\
    generate_default_groups_acls, generate_local_admin_rights, generate_default_dc_groups_acls, generate_default_users_acls,\
    generate_all_extended_rights, generate_generic_write, generate_owns,\
    generate_write_dacl, generate_write_owner, generate_generic_all, generate_outbound_acls
from adsimulator.generators.computers import generate_computers, generate_dcs, generate_default_admin_to,\
get_tiered_objects_2,\
    generate_can_rdp_relationships_on_it_users, generate_dcom_relationships_on_it_users,\
    generate_can_rdp_relationships_on_it_groups, generate_dcom_relationships_on_it_groups,\
    generate_allowed_to_delegate_relationships_on_it_users, generate_sessions,\
    generate_allowed_to_delegate_relationships_on_computers, assign_unconstrained_delegation,\
    generate_can_ps_remote_relationships_on_it_users, generate_can_ps_remote_relationships_on_it_groups
from adsimulator.generators.users import generate_guest_user, generate_default_account, generate_administrator, generate_krbtgt_user,\
    generate_users, link_default_users_to_domain, assign_kerberoastable_users
from adsimulator.generators.groups import generate_groups, generate_domain_administrators, generate_default_member_of, nest_groups,\
    assign_users_to_group,\
    get_tiered_objects_1
from adsimulator.utils.data import get_names_pool, get_surnames_pool, get_parameters_from_json, get_domains_pool
from adsimulator.utils.domains import get_domain_dn
from adsimulator.utils.parameters import print_all_parameters, get_int_param_value, get_int_param_value_with_upper_limit,\
    get_perc_param_value
from adsimulator.templates.default_values import DEFAULT_VALUES
from adsimulator.utils.updates import install_updates
from adsimulator.utils.about import print_software_information
from adsimulator.templates.ous import STATES

def cn(name,domain):
    return f"{name}@{domain}"
 
def cs(relative_id,base_sid):
    return f"{base_sid}-{str(relative_id)}"

def generate_permission(session,users,computers):
    count = int(math.floor(len(computers) * .1))
    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(users)
        props.append({'a': user, 'b': comp})

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanRDP]->(m)', props=props)

    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(users)
        props.append({'a': user, 'b': comp})

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ExecuteDCOM]->(m)', props=props)

    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(users)
        props.append({'a': user, 'b': comp})

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:AllowedToDelegate]->(m)', props=props)

    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(users)
        props.append({'a': user, 'b': comp})

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ReadLAPSPassword]->(m)', props=props)
 


def generate_ACL(session,ace,source,target):
    ace_string = '[r:' + ace + '{isacl:true}]'
    session.run(
    'MERGE (n:Group {name:$group}) MERGE (m {name:$principal}) MERGE (n)-' + ace_string + '->(m)', group=source, principal=target)
 



class Messages():
    def title(self):
        print("==================================================================")
        print(
        """

      ,.,
      MMMM_    ,..,
        \"_ \"__"MMMMM          ,...,,
 ,..., __.\" --\"    ,.,     _-\"MMMMMMM
MMMMMM"___ "_._   MMM"_."" _ """"""         _     _                 _       _               
 \"\"\"\"\"    \"\" , \_.   \"_. .\"  __ _  __| |___(_)_ __ ___  _   _| | __ _| |_ ___  _ __    
        ,., _"__ \__./ ."   / _` |/ _` / __| | '_ ` _ \| | | | |/ _` | __/ _ \| '__|   
       MMMMM_"  "_    ./   | (_| | (_| \__ \ | | | | | | |_| | | (_| | || (_) | | 
        ''''      (    )    \__,_|\__,_|___/_|_| |_| |_|\__,_|_|\__,_|\__\___/|_|  
 ._______________.-'____\"---._.
  \                          /
   \________________________/
   (_)                    (_)

                                                         
                                                          
        """
        )
        print(" A realistic simulator of Active Directory domains\n")
        print("==================================================================")


    def input_default(self, prompt, default):
        return input("%s [%s] " % (prompt, default)) or default


    def input_yesno(self, prompt, default):
        temp = input(prompt + " " + ("Y" if default else "y") + "/" + ("n" if default else "N") + " ")
        if temp == "y" or temp == "Y":
            return True
        elif temp == "n" or temp == "N":
            return False
        return default



class MainMenu(cmd.Cmd):

    def __init__(self):
        self.m = Messages()
        self.url = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = "adslab"
        self.use_encryption = False
        self.driver = None
        self.connected = False
        self.old_domain = None
        self.domain = "TESTLAB.LOCALE"
        self.current_time = int(time.time())
        self.base_sid = "S-1-5-21-883232822-274137685-4173207997"
        self.first_names = get_names_pool()
        self.last_names = get_surnames_pool()
        self.domain_names = get_domains_pool()
        self.parameters_json_path = "DEFAULT"
        self.parameters = DEFAULT_VALUES
        self.json_file_name = None
        self.level = "Medium"

        cmd.Cmd.__init__(self)


    def cmdloop(self):
        while True:
            self.m.title()
            self.do_help("")
            try:
                cmd.Cmd.cmdloop(self)
            except KeyboardInterrupt:
                if self.driver is not None:
                    self.driver.close()
                raise KeyboardInterrupt


    def help_dbconfig(self):
        print("Configure database connection parameters")


    def help_connect(self):
        print("Test connection to the database and verify credentials")

 
    def help_setdomain(self):
        print("Set domain name (default 'TESTLAB.LOCAL')")

 
    def help_cleardb(self):
        print("Clear the database and set constraints")

 
    def help_generate(self):
        print("Connect to the database, clear the db, set the schema, and generate random data")


    def help_setparams(self):
        print("Import the settings JSON file containing the parameters for the graph generation")
    

    def help_update(self):
        print("Check for available updates")


    def help_about(self):
        print("View information about adsimulator")

 
    def help_exit(self):
        print("Exit")
    

    def do_update(self, args):
        install_updates()
        
    

    def do_about(self, args):
        print_software_information()

 
    def do_dbconfig(self, args):
        print("Current Settings:")
        print("DB Url: {}".format(self.url))
        print("DB Username: {}".format(self.username))
        print("DB Password: {}".format(self.password))
        print("Use encryption: {}".format(self.use_encryption))
        print("")
        
        # Level of security
        self.level = self.m.input_default(
            "Enter level of Security (Medium/Medium) ", self.level)

        print("")
        print("New Settings:")
        print("Level of Security: {}".format(self.level))
        print("")
        print("Testing DB Connection")
        self.test_db_conn()

 
    def do_setdomain(self, args):
        passed = args
        if passed != "":
            try:
                self.domain = passed.upper()
                return
            except ValueError:
                pass

        self.domain = self.m.input_default("Domain", self.domain).upper()
        print("")
        print("New Settings:")
        print("Domain: {}".format(self.domain))


    def do_exit(self, args):
        raise KeyboardInterrupt

 
    def do_connect(self, args):
        self.test_db_conn()


    def do_cleardb(self, args):
        if not self.connected:
            print("Not connected to database. Use connect first")
            return

        print("Clearing Database")
        d = self.driver
        session = d.session()

        session.run("match (a) -[r] -> () delete a, r")
        session.run("match (a) delete a")

        session.close()

        print("DB Cleared and Schema Set")
    

    def do_setparams(self, args):
        passed = args
        if passed != "":
            try:
                json_path = passed
                self.parameters = get_parameters_from_json(json_path)
                self.parameters_json_path = json_path
                print_all_parameters(self.parameters)
                return
            except ValueError:
                pass

        json_path = self.m.input_default("Parameters JSON file", self.parameters_json_path)
        self.parameters = get_parameters_from_json(json_path)
        if self.parameters == DEFAULT_VALUES:
            self.parameters_json_path = "DEFAULT"
        else:
            self.parameters_json_path = json_path
        self.parameters = get_parameters_from_json(json_path)
        print_all_parameters(self.parameters)


    def test_db_conn(self):
        self.connected = False
        if self.driver is not None:
            self.driver.close()
        try:
            self.driver = GraphDatabase.driver(
                self.url, auth=(self.username, self.password), encrypted=self.use_encryption)
            self.connected = True
            print("Database Connection Successful!")
        except:
            self.connected = False
            print("Database Connection Failed. Check your settings.")


    def do_generate(self, args):
        passed = args
        if passed != "":
            try:
                self.json_file_name = passed
            except ValueError:
                self.json_file_name = None

        self.test_db_conn()
        self.do_cleardb("a")
        
        # self.generate_data_low()
        self.generate_data()
        self.old_domain = self.domain


    def generate_data(self):
        if not self.connected:
            print("Not connected to database. Use connect first")
            return
        
        domain_dn = get_domain_dn(self.domain)

        computers = []
        computer_properties_list = []
        dc_properties_list = []
        groups = []
        users = []
        user_properties_list = []
        gpos = []
        gpos_properties_list = []
        ou_guid_map = {}
        ou_properties_list = []
        
        session = self.driver.session()

        print("Starting data generation")

        print("Generating the", self.domain, "domain")
        functional_level = generate_domain(session, self.domain, self.base_sid, domain_dn, self.parameters)
        
        print("Generating the default domain groups")
        generate_default_groups(session, self.domain, self.base_sid, self.old_domain)   

        ddp = str(uuid.uuid4()).upper()
        ddcp = str(uuid.uuid4()).upper()
        dcou = str(uuid.uuid4()).upper()
    
        print("Generating default GPOs")
        generate_default_gpos(session, self.domain, domain_dn, ddp, ddcp)

        print("Generating Domain Controllers OU")
        generate_domain_controllers_ou(session, self.domain, domain_dn, dcou)

        print("Linking Default GPOs")
        link_default_gpos(session, self.domain, ddp, ddcp, dcou)

        # ENTERPRISE ADMINS
        print("Generating Enterprise Admins ACLs")
        # Adding Ent Admins -> Medium Value Targets
        generate_enterprise_admins_acls(session, self.domain)


        # ADMINISTRATORS
        # Adding Administrators -> Medium Value Targets
        print("Generating Administrators ACLs")
        generate_administrators_acls(session, self.domain)


        # DOMAIN ADMINS
        # Adding Domain Admins -> Medium Value Targets
        print("Generating Domain Admins ACLs")
        generate_domain_admins_acls(session, self.domain)


        # DC Groups
        # Extra ENTERPRISE READ-ONLY DOMAIN CONTROLLERS
        print("Generating DC groups ACLs")
        generate_default_dc_groups_acls(session, self.domain)

        # ---------------------------------------------------
        # 3 TIERS
        print("Creating Tierd OUs")
        # Creating root OUs
        base_statement = "MERGE (n:Base {name: $uname}) SET n:OU, n.objectid=$guid"
        OU_names = ['Admin','Groups','Quarantine','Workstations','Tire 1 servers','User Accounts']
        for name in OU_names:
            session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(name,self.domain))
            session.run( 'MERGE (n:OU {name:$uname}) WITH n MERGE (m:Domain {name:$domain}) WITH n,m MERGE (m)-[:Contains]->(n)', uname=cn(name,self.domain), domain=self.domain)
 
        # Tierd OUs
        Tierd_OU = {'Tier 0':['T0_Accounts','T0_Devices','T0_Groups','T0_Service Accounts'],
                    'Tier 1':['T1_Accounts','T1_Devices','T1_Groups','T1_Service Accounts'],
                    'Tier 2':['T2_Accounts','T2_Devices','T2_Groups','T2_Service Accounts']}
        for key in Tierd_OU.keys():
            session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(key,self.domain))
            session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('Admin',self.domain), gname=cn(key,self.domain))
            for sub in Tierd_OU[key]:
                session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(sub,self.domain))
                session.run(
                    'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn(key,self.domain), gname=cn(sub,self.domain))
 
        # Groups OU
        sub_group =['Distribution Groups','Security Groups']
        for name in sub_group:
            session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(name,self.domain))
            session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('Groups',self.domain), gname=cn(name,self.domain))
 
        # Workstations OU
        # Retrieve states from template
        for name in STATES:
            session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(name,self.domain))
            session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('Workstations',self.domain), gname=cn(name,self.domain))
 
        # User Accounts OU
        session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn('Enabled Users',self.domain))
        session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('User Accounts',self.domain), gname=cn('Enabled Users',self.domain))
        session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn('Disabled Users',self.domain))
        session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('User Accounts',self.domain), gname=cn('Disabled Users',self.domain))
 
        # T1 services
        sub_service = ['Application','Print','Database','Exchange','Remote Desktop']
        for name in sub_service:
            session.run(f"{base_statement}",guid = str(uuid.uuid4()),uname=cn(name,self.domain))
            session.run(
                'MERGE (n:OU {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (n)-[:Contains]->(m)', name=cn('Tire 1 servers',self.domain), gname=cn(name,self.domain))
 

        # -------------------------------------------------------------
        
        # GPOs
        # print("Creating GPOs for 3 Tiers")
        #Creating GPOs for the root OUs
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('Restrict Server Logon',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('Restrict Server Logon',self.domain), uname=cn('Tire 1 servers',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('Restrict Workstation Logon',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('Restrict Workstation Logon',self.domain), uname=cn('Workstations',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('New_PC Configuration',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('New_PC Configuration',self.domain), uname=cn('Quarantine',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('Admins Configuration',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('Admins Configuration',self.domain), uname=cn('Admin',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('Normal_Users Configuration',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('Normal_Users Configuration',self.domain), uname=cn('User Accounts',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('Group Configuration',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('Normal_Users Configuration',self.domain), uname=cn('Groups',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('PAW Configuration',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('PAW Configuration',self.domain), uname=cn('T0_Devices',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('PAW Outbound restrictions',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('PAW Outbound restrictions',self.domain), uname=cn('T0_Devices',self.domain))
        session.run(
                "MERGE (n:Base {name:$gponame}) SET n:GPO, n.objectid=$guid", gponame=cn('RestrictedAdmin Required -Computer',self.domain), guid=str(uuid.uuid4()))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('RestrictedAdmin Required -Computer',self.domain), uname=cn('T1_Devices',self.domain))
        session.run(
                "MERGE (n:GPO {name:$gponame}) WITH n MERGE (m:OU {name:$uname}) WITH n,m MERGE (n)-[r:GpLink]->(m)", gponame=cn('RestrictedAdmin Required -Computer',self.domain), uname=cn('T2_Devices',self.domain))





        # --------------------------------------------------------------
        # DEFAULT USERS
        print("Generating default users")
        generate_guest_user(session, self.domain, self.base_sid, self.parameters)
        generate_default_account(session, self.domain, self.base_sid, self.parameters)
        generate_administrator(session, self.domain, self.base_sid, self.parameters)
        generate_krbtgt_user(session, self.domain, self.base_sid, self.parameters)
        link_default_users_to_domain(session, self.domain, self.base_sid)


        # Generating users
        num_users = get_int_param_value("User", "nUsers", self.parameters)
        print("Generating", str(num_users), "users")
        ridcount = 0

        disable_users = []

        user_properties_list, users, disable_users, ridcount = generate_users(session, self.domain, self.base_sid, num_users, self.current_time, self.first_names, self.last_names, users, disable_users, ridcount, self.parameters)

        admin = random.sample(users,int(num_users*DEFAULT_VALUES['Admin_Percentage']))
        normal_users = [i for i in users if i not in admin]


        # Adminstrator account to Medium Value Targets
        base_statement = "MERGE (n:Base {name: $uname}) SET n:User,n.objectid=$sid"
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("DOMAIN ADMINS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("ENTERPRISE ADMINS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("PRINT OPERATORS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("BACKUP OPERATORS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("SERVER OPERATORS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("ACCOUNT OPERATORS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("DOMAIN CONTROLLERS",self.domain))
        session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=cn("ADMINSTRATOR",self.domain), gname=cn("GROUP POLICY CREATOR OWNERS",self.domain))


        #Assign Tiered admins Users
        Tiered_OU_percentage = DEFAULT_VALUES['Tiered_Accounts']
        Tiered_OU = [cn('T0_Accounts',self.domain)]*Tiered_OU_percentage[0] + [cn('T1_Accounts',self.domain)]*Tiered_OU_percentage[1] + [cn('T2_Accounts',self.domain)]*Tiered_OU_percentage[2]
        T0_group = [cn("PRINT OPERATORS",self.domain),cn("ACCOUNT OPERATORS",self.domain),cn("SERVER OPERATORS",self.domain),cn("DOMAIN ADMINS",self.domain)]
        T1_group = [cn("T1 Admins",self.domain),cn("T1 PAW maintenances",self.domain),cn("T1 service Accounts",self.domain),cn("T1 Management",self.domain)]
        T2_group = [cn("T2 Admins",self.domain),cn("T2 PAW maintenances",self.domain),cn("T2 service Accounts",self.domain),cn("T2 Management",self.domain)]
        for group_name in T1_group + T2_group:
            props =[]
            sid = cs(ridcount,self.base_sid)
            ridcount += 1
            props.append({'name': group_name, 'id': sid})
            session.run(
                'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
 
        T0_users =[]
        T1_users =[]
        T2_users =[]
        for user in admin:
            OU_name = random.choice(Tiered_OU)
            if OU_name == cn('T0_Accounts',self.domain):
                T0_users.append(user)
                if random.choice([1]*DEFAULT_VALUES['T0_Accounts'][0]+[0]*DEFAULT_VALUES['T0_Accounts'][1]):
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=OU_name)
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=user, gname= random.choice(T0_group))
                else:
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=cn("T0_Service Accounts",self.domain))
            if OU_name == cn('T1_Accounts',self.domain):
                T1_users.append(user)
                temp_name = random.choice(T1_group)
                session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=user, gname= temp_name)
                if temp_name == cn("T1 service Accounts",self.domain):
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=cn('T1_Service Accounts',self.domain))
                else:
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=OU_name)
            if OU_name == cn('T2_Accounts',self.domain):
                T2_users.append(user)
                temp_name = random.choice(T2_group)
                session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf]->(m)', name=user, gname= temp_name)
                if temp_name == cn("T2 service Accounts",self.domain):
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=cn('T2_Service Accounts',self.domain))
                else:
                    session.run(
                    'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=OU_name)
 

        #Place disable users and normal users
        for user in normal_users:
            session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=cn('Enabled Users',self.domain))
        for user in disable_users:
            session.run(
                'MERGE (n:User {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=user, gname=cn('Disabled Users',self.domain))
 
        #Place groups
        for group in T0_group:
            session.run(
                'MERGE (n:Group {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=group, gname=cn('T0_Groups',self.domain))
        for group in T1_group:
            session.run(
                'MERGE (n:Group {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=group, gname=cn('T1_Groups',self.domain))
        for group in T2_group:
            session.run(
                'MERGE (n:Group {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=group, gname=cn('T2_Groups',self.domain))
 




        # Creating DOMAIN CONTROLLERS
        print("Creating Domain Controllers")
        num_ous = get_int_param_value_with_upper_limit("OU", "nOUs", self.parameters, DEFAULT_VALUES["Half_Figure"])
        if not num_ous % 2 == 0:
            num_ous = num_ous - 1
        num_states = int(num_ous / 2)
 
        print("Generating", str(num_states), "Domain Controllers")
        dc_properties_list, ridcount = generate_dcs(session, self.domain, self.base_sid, domain_dn, num_states, dcou, ridcount, self.current_time, self.parameters, functional_level)
 
 
        # Creating COMPUTER Nodes
        num_computers = get_int_param_value("Computer", "nComputers", self.parameters)
        print("Generating", str(num_computers), "computers")
 
        PAW = []
        computer_properties_list, computers, ridcount, PAW, Server, Workingstation = generate_computers(session, self.domain, self.base_sid, num_computers, computers, self.current_time, self.parameters)
 


        #Place PAW
        Tier_name =['T0_','T1_','T2_']
        T0_PAW =[]
        T1_PAW=[]
        T2_PAW =[]
        for pc in PAW:
            i = random.choice(Tier_name)
            session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn(i+'Devices',self.domain))
            if i == 'T0_':
                T0_PAW.append(pc)
            elif i == 'T1_':
                T1_PAW.append(pc)
            else:
                T2_PAW.append(pc)
 
 
        # #Place T1server
        # query = session.run('MATCH(n:OU {name:$uname})-[:Contains]->(o:OU) RETURN o.name',uname = cn('Tire 1 servers',self.domain)).data()
        # Server_sub = [list(i.values())[0] for i in query]
        # for pc in Server:
        #     session.run(
        #         'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=random.choice(Server_sub))

        #Place Server
        T0_Server=[]
        T1_Server=[]
        T2_Server =[]
        for pc in Server:
            num = random.choice(range(10, 101))
            if num <= 90:
                T0_Server.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T0_Server',self.domain))
            elif (num > 90) and (num <= 95):
                T1_Server.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T1_Server',self.domain))
            else:
                T2_Server.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T2_Server',self.domain))
 
        # #Place workstations
        # query = session.run('MATCH(n:OU {name:$uname})-[:Contains]->(o:OU) RETURN o.name',uname = cn('Workstations',self.domain)).data()
        # WS_sub = [list(i.values())[0] for i in query]
        # for pc in Workingstation:
        #     session.run(
        #         'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=random.choice(WS_sub))

        #Place Workstation
        T0_Workstation=[]
        T1_Workstation=[]
        T2_Workstation =[]
        for pc in Workingstation:
            num = random.choice(range(10, 101))
            if num == 1:
                T0_Workstation.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T0_Workstation',self.domain))
            elif (num > 1) and (num <= 10):
                T1_Workstation.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T1_Workstation',self.domain))
            else:
                T2_Workstation.append(pc)
                session.run(
                'MERGE (n:Computer {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=pc, gname=cn('T2_Workstation',self.domain))
 


        
        # Distribution groups and Security groups
        # In ADCreator, generate all groups for both types, with all states
        # However, here, there is a constrained number of groups
        
        num_groups = get_int_param_value("Group", "nGroups", self.parameters)
        print("Generating groups")
        group_properties_list, groups, ridcount = generate_groups(session, self.domain, self.base_sid, domain_dn, num_groups, groups, ridcount, self.parameters)
        
        # Adding Domain Admins to Local Admins of Computers
        print("Adding Domain Admins to Local Admins of Computers")
        generate_default_admin_to(session, self.base_sid)

        das = generate_domain_administrators(session, self.domain, num_users, users)

        print("Adding members to default groups")
        generate_default_member_of(session, self.domain, self.base_sid, self.old_domain)

        # GROUP NESTING
        # nesting_perc = get_perc_param_value("Group", "nestingGroupProbability", self.parameters)
        # print("Applying random group nesting (nesting probability:", str(nesting_perc), "%)")
        # nest_groups(session, num_groups, groups, nesting_perc)

        # ADDING Users to Groups
        print("Adding users to groups")
        # dist_group = [], sec_group = []
        get_tiered_objects_1(T0_users, T1_users, T2_users, T0_group, T1_group, T2_group)
        it_users, dist_group, sec_group = assign_users_to_group(session, normal_users, das, self.domain)


        # Generate Permissions
        print("Generating permissions")
        #ACCOUNT OPERATORS can modfify accounts of most groups
        all_groups = session.run("""MATCH (n:Group) WHERE not(n.name CONTAINS "ADMINISTRATORS") AND (n.name CONTAINS $domain_name) AND not((n)-[:MemberOf]->(:Group{name:$gname}))
                                            RETURN n.name""",domain_name = self.domain,gname=cn("ADMINISTRATORS",self.domain))
        for temp in all_groups:
            session.run(
            'MERGE (n:Group {name:$gname}) WITH n MERGE (m:Group {name:$mname}) WITH n,m MERGE (n)-[:GenericAll {isacl:true}]->(m)', gname=cn("ACCOUNT OPERATORS",self.domain), mname=temp["n.name"])
 
        # Print Operators and Server Operators can log into domain controllers
 
        query = session.run("""MATCH (n:User) -[:MemberOf]->(:Group{name:$gname})
                                            RETURN n.name""",gname = cn("SERVER OPERATORS",self.domain)).data()
        s_Operators = [list(i.values())[0] for i in query]
        query = session.run("""MATCH (n:User) -[:MemberOf]->(:Group{name:$gname})
                                            RETURN n.name""",gname = cn("PRINT OPERATORS",self.domain))
        p_Operators = [list(i.values())[0] for i in query]
        query = session.run("MATCH (n:Computer)-[:MemberOf]->(:Group{name:$gname}) RETURN n.name",gname = cn("DOMAIN CONTROLLERS",self.domain)).data()
        DCs =  [list(i.values())[0] for i in query]
        for OP in s_Operators+p_Operators:
            for DC in DCs:
                if random.choice([True, False]):
                    session.run('MERGE (n:User {name:$uname}) WITH n MERGE (m:Computer {name:$cname}) WITH n,m MERGE (m)-[:HasSession]->(n)', uname=OP,cname = DC)
 
        query = session.run("""MATCH (n:User) -[:MemberOf]->(:Group{name:$gname})
                                            RETURN n.name""",gname = cn("SERVER OPERATORS",self.domain)).data()
 




        it_groups = generate_local_admin_rights(session, groups, computers)
        # IT_GROUPS
        depart = ['IT','HR','MARKETING','OPERATIONS','BIDNESS']
        department_collections = {}
        for item in depart:
            department_collections[item] = [[], []]
            # Groups
            department_collections[item][0] = [x for x in groups if item in x]

            # Users
            if item == 'IT':
                department_collections[item][1] = it_users
            else: 
                department_collections[item][1] = [x for x in normal_users if item in x]
        


        print("Adding ACLs for default groups")
        generate_default_groups_acls(session, self.domain, self.base_sid)
        
        print("Adding ACLs for default users")
        generate_default_users_acls(session, self.domain, self.base_sid)
        
        print("Adding AllExtendedRights")
        generate_all_extended_rights(session, self.domain, self.base_sid, user_properties_list, das)
        #send tiered objects to the computers script
        get_tiered_objects_2(T0_users, T1_users, T2_users, T0_PAW, T1_PAW, T2_PAW, T0_Server, T1_Server, T2_Server, T0_Workstation, T1_Workstation, T2_Workstation, T0_group, T1_group, T2_group)
        
        print("Adding extra edges")
        for item in depart:
            print(item, ": ", len(department_collections[item][0]), " ", len(department_collections[item][1]))
            if len(department_collections[item][1]) > 0:
                can_rdp_users_perc = get_perc_param_value("Computer", "CanRDPFromUserPercentage", self.parameters)
                count = int(math.floor(len(computers) * (can_rdp_users_perc / 100)))
                print("Adding a maximum of", str(count), "CanRDP from users")
                generate_can_rdp_relationships_on_it_users(session, computers, department_collections[item][1], count)

                dcom_users_perc = get_perc_param_value("Computer", "ExecuteDCOMFromUserPercentage", self.parameters)
                count = int(math.floor(len(computers) * (dcom_users_perc / 100)))
                print("Adding a maximum of", str(count), "ExecuteDCOM from users")
                generate_dcom_relationships_on_it_users(session,computers, department_collections[item][1], count)

                allowed_to_delegate_users_perc = get_perc_param_value("Computer", "AllowedToDelegateFromUserPercentage", self.parameters)
                count = int(math.floor(len(computers) * (allowed_to_delegate_users_perc / 100)))
                print("Adding a maximum of", str(count), "AllowedToDelegate from users")
                generate_allowed_to_delegate_relationships_on_it_users(session, computers, department_collections[item][1], count)
                
                ps_remote_users_perc = get_perc_param_value("Computer", "CanPSRemoteFromUserPercentage", self.parameters)
                count = int(math.floor(len(computers) * (ps_remote_users_perc / 100)))
                print("Adding a maximum of", str(count), "CanPSRemote from users")
                generate_can_ps_remote_relationships_on_it_users(session, computers, department_collections[item][1], count)
            

            if len(department_collections[item][0]) > 0:
                can_rdp_groups_perc = get_perc_param_value("Computer", "CanRDPFromGroupPercentage", self.parameters)
                count = int(math.floor(len(computers) * (can_rdp_groups_perc / 100)))
                print("Adding a maximum of", str(count), "CanRDP from groups")
                generate_can_rdp_relationships_on_it_groups(session, computers, department_collections[item][0], count)
                
                dcom_groups_perc = get_perc_param_value("Computer", "ExecuteDCOMFromGroupPercentage", self.parameters)
                count = int(math.floor(len(computers) * (dcom_groups_perc / 100)))
                print("Adding a maximum of", str(count), "ExecuteDCOM from groups")
                generate_dcom_relationships_on_it_groups(session, computers, department_collections[item][0], count)
                
                ps_remote_groups_perc = get_perc_param_value("Computer", "CanPSRemoteFromGroupPercentage", self.parameters)
                count = int(math.floor(len(computers) * (ps_remote_groups_perc / 100)))
                print("Adding a maximum of", str(count), "CanPSRemote from groups")
                generate_can_ps_remote_relationships_on_it_groups(session, computers, department_collections[item][0], count)

        allowed_to_delegate_computers_perc = get_perc_param_value("Computer", "AllowedToDelegateFromComputerPercentage", self.parameters)
        count = int(math.floor(len(computers) * (allowed_to_delegate_computers_perc / 100)))
        print("Adding a maximum of", str(count), "AllowedToDelegate from computers")
        generate_allowed_to_delegate_relationships_on_computers(session, computers, count)
        
        print("Adding sessions")
        generate_sessions(self.level, session, num_users, normal_users, Workingstation, Server, T0_users, T1_users, T2_users, T0_PAW,T1_PAW,T2_PAW)

        print("Generating ACEs")
        #T0 users can has permissions to any level
        generate_permission(session,T0_users,PAW+Server+Workingstation)
        #T1 users can has permissions to level1 and 2
        generate_permission(session,T1_users,T1_PAW+T2_PAW+Server+Workingstation)
        #T2 users can has permissions to level2
        generate_permission(session,T2_users,T2_PAW+Workingstation)

        acl_types = ["AllExtendedRights", "GenericAll", "GenericWrite", "Owns", "WriteDACL", "WriteOwner", "AddMember"]
        acl_percentages = DEFAULT_VALUES["ACL_percentages"]

        acl_list = []
        for i in range(len(acl_types)):
            acl_list += acl_types[i]*acl_percentages[i]

        # acl_list = ["AllExtendedRights"]*3+["GenericAll"]*40+["GenericWrite"]*20+["Owns"]*10+["WriteDACL"]*10+["WriteOwner"]*10+["AddMember"]*7
        T0_principals = T0_users + T0_group + T1_users +T1_group + T2_users +T2_group
        T1_principals = T1_users +T1_group + T2_users +T2_group +dist_group +sec_group
        T2_principals = T2_users +T2_group + dist_group +sec_group
 
        for i in T1_group:
            for j in range(random.randint(1, int(len(T1_principals)*DEFAULT_VALUES["Half"]))):
                ace = random.choice(acl_list)
                if ace == "AddMember":
                    p = random.choice(T1_group + T2_users +T2_group +dist_group +sec_group)
                else:
                    p = random.choice(T1_principals)
                generate_ACL(session,ace,i,p)
 
        for i in T2_group:
            for j in range(random.randint(1, int(len(T1_principals)*DEFAULT_VALUES["Half"]))):
                ace = random.choice(acl_list)
                if ace == "AddMember":
                    p = random.choice(T2_users +T2_group + dist_group +sec_group)
                else:
                    p = random.choice(T2_principals)
                generate_ACL(session,ace,i,p)
 
        for i in T0_users:
            for j in range(random.randint(1, int(len(T0_principals)*DEFAULT_VALUES["Half"]))):
                p = random.choice(T0_principals)
                ace_string = '[r:' + ace + '{isacl:true}]'
                session.run(
                'MERGE (n:User {name:$group}) MERGE (m {name:$principal}) MERGE (n)-' + ace_string + '->(m)', group=i, principal=p)
 
 
        print("Adding Admin rights")
        session.run(
                'MATCH (n:Computer) WHERE (n.name CONTAINS $domain_name) MATCH (m:Group {name:$gname}) MERGE (m)-[:AdminTo]->(n)',domain_name = self.domain, gname=cn("DOMAIN ADMINS",self.domain))
        for pc in T1_PAW:
            session.run(
                'MATCH (n:Group {name:$gname}) WHERE (n.name CONTAINS $domain_name) MERGE (m:Computer {name:$pname}) MERGE (n)-[:AdminTo]->(m)',domain_name = self.domain, gname=cn("T1 Admins",self.domain),pname = pc)
        for pc in T2_PAW:
            session.run(
                'MATCH (n:Group {name:$gname}) WHERE (n.name CONTAINS $domain_name) MERGE (m:Computer {name:$pname}) MERGE (n)-[:AdminTo]->(m)',domain_name = self.domain, gname=cn("T2 Admins",self.domain),pname = pc)


        # print("Adding Domain Admin ACEs")
        group_name = cn("DOMAIN ADMINS",self.domain)
        props = []
        query = session.run('MATCH (n:Group) WHERE (n.name CONTAINS $domain_name)RETURN n.name',domain_name = self.domain).data()
        groups = [list(i.values())[0] for i in query]
        query = session.run('MATCH (n:Computer) WHERE (n.name CONTAINS $domain_name)RETURN n.name',domain_name = self.domain).data()
        computers = [list(i.values())[0] for i in query]
        query = session.run('MATCH (n:User) WHERE (n.name CONTAINS $domain_name)RETURN n.name',domain_name = self.domain).data()
        users = [list(i.values())[0] for i in query]
        query = session.run('MATCH (n:GPO) WHERE (n.name CONTAINS $domain_name)RETURN n.name',domain_name = self.domain).data()
        all_GPOs = [list(i.values())[0] for i in query]
        for x in computers:
            props.append({'name': x})
            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:Computer {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []
 
        session.run(
            'UNWIND $props as prop MATCH (n:Computer {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
 
        for x in all_GPOs:
            props.append({'name': x})
            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:GPO {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:Owns {isacl:true}]->(n)', props=props, gname=group_name)
                props = []
 
        session.run(
            'UNWIND $props as prop MATCH (n:GPO {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:Owns {isacl:true}]->(n)', props=props, gname=group_name)
 
 
        props = []
        for x in users:
            props.append({'name': x})
 
            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:User {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []
 
        session.run(
            'UNWIND $props as prop MATCH (n:User {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
 
        for x in groups:
            props.append({'name': x})
 
            if len(props) > 500:
                session.run(
                    'UNWIND $props as prop MATCH (n:Group {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
                props = []
 
        session.run(
            'UNWIND $props as prop MATCH (n:Group {name:prop.name}) WITH n MATCH (m:Group {name:$gname}) WITH m,n MERGE (m)-[r:GenericAll {isacl:true}]->(n)', props=props, gname=group_name)
 


        acl_principals_perc = get_perc_param_value("ACLs", "ACLPrincipalsPercentage", self.parameters)
        num_acl_principals = int(round(len(department_collections['IT'][0]) * (acl_principals_perc / 100)))
        generate_outbound_acls(session, num_acl_principals, department_collections['IT'][0], department_collections['IT'][1], all_GPOs, computers, self.parameters)

        session.run('MATCH (n) SET n.domain=$domain', domain=self.domain)

        self.domain_names = get_domains_pool()
        generate_trusts(session, self.domain, self.domain_names, self.parameters)

        session.run('MATCH (n:User) SET n.owned=false')

        owned_user = random.choice(users)
        print("Compromised user:", owned_user)

        session.run('MATCH (n:User {name: $owneduser}) SET n.owned=true', owneduser=owned_user)
        session.run('MATCH (n:User {name: $owneduser}) SET n:Compromised', owneduser=owned_user)

        session.run('MATCH (n:Computer) SET n.owned=false')

        if self.json_file_name is not None:
            self.write_json(session)

        session.close()

        print("Database Generation Finished!")


    def write_json(self, session):
        json_path = os.getcwd() + "/" + self.json_file_name
        query = "CALL apoc.export.json.all('" + json_path + "',{useTypes:true})"
        session.run(query)
        print("Graph exported in", json_path)
