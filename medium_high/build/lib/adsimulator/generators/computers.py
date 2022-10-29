import random
import math
from adsimulator.utils.principals import get_sid_from_rid, get_name, get_dn
from adsimulator.utils.computers import get_computer_dn, get_computer_name,\
    generate_client_service_pricipal_names, generate_server_service_pricipal_names,\
    is_os_vulnerable
from adsimulator.utils.boolean import generate_boolean_value
from adsimulator.utils.time import generate_timestamp
from adsimulator.utils.ous import get_ou_dn
from adsimulator.utils.parameters import get_perc_param_value, get_dict_param_value,\
    print_computer_generation_parameters, print_dc_generation_parameters
from adsimulator.templates.ous import STATES
from adsimulator.templates.computers import get_client_os_list, get_server_os_list, get_main_dc_os
from adsimulator.templates.default_values import get_complementary_value, DEFAULT_VALUES

buffer_threshold = DEFAULT_VALUES["Buffer_Threshold"]

T0_user_arr = []
T1_users_arr = []
T2_users_arr = []
T0_PAW_arr = []
T1_PAW_arr = []
T2_PAW_arr = []
T0_Server_arr = []
T1_Server_arr = []
T2_Server_arr = []
T0_Workstation_arr = []
T1_Workstation_arr = []
T2_Workstation_arr = []
T0_group_arr = []
T1_group_arr = []
T2_group_arr = []

def generate_computers(session, domain_name, domain_sid, num_nodes, computers, current_time, parameters):
    computer_properties_list = []
    group_name = "DOMAIN COMPUTERS@{}".format(domain_name)
    props = []
    ridcount = 1103
    enabled_perc = get_perc_param_value("Computer", "enabled", parameters)
    has_laps_perc = get_perc_param_value("Computer", "haslaps", parameters)
    unconstrained_delegation_perc = get_perc_param_value("Computer", "unconstraineddelegation", parameters)
    os_perc = get_dict_param_value("Computer", "osProbability", parameters)
    os_list = get_client_os_list(os_perc)
 
    # New params
    privesc_perc = get_perc_param_value("Computer", "privesc", parameters)
    creddump_perc = get_perc_param_value("Computer", "creddump", parameters)
    exploitable_perc = get_perc_param_value("Computer", "exploitable", parameters)
 
    # PC List
    PC_list = ['PAW']*10+['Server']*10 + ['Workstation']*80
    PAW = []
    Server = []
    Workingstation =[]
 
    print_computer_generation_parameters(enabled_perc, has_laps_perc, unconstrained_delegation_perc, os_perc)
    for i in range(1, num_nodes + 1):
        PC_type = random.choices(PC_list)[0]
        if PC_type == 'PAW':
            comp_name = str('PAW')+"-{:05d}@{}".format(len(PAW), domain_name)
            PAW.append(comp_name)
        elif PC_type == 'Server':
            comp_name = str('S')+"-{:05d}@{}".format(len(Server), domain_name)
            Server.append(comp_name)
        else:
            comp_name = str('WS')+"-{:05d}@{}".format(len(Workingstation), domain_name)
            Workingstation.append(comp_name)
 
        computers.append(comp_name)
        os = random.choice(os_list)
        enabled = generate_boolean_value(enabled_perc, get_complementary_value(enabled_perc))
        has_laps = generate_boolean_value(has_laps_perc, get_complementary_value(has_laps_perc))
        unconstrained_delegation = generate_boolean_value(unconstrained_delegation_perc, get_complementary_value(unconstrained_delegation_perc))
 
        # New params
        privesc = generate_boolean_value(privesc_perc, get_complementary_value(privesc_perc))
        creddump = generate_boolean_value(creddump_perc, get_complementary_value(creddump_perc))
        if is_os_vulnerable(os):
            exploitable = generate_boolean_value(exploitable_perc, get_complementary_value(exploitable_perc))
        else:
            exploitable = False
 
        computer_property = {
            'id': get_sid_from_rid(ridcount, domain_sid),
            'props': {
                'name': comp_name,
                'operatingsystem': os,
                'enabled': enabled,
                'haslaps': has_laps,
                'highvalue': False,
                'lastlogontimestamp': generate_timestamp(current_time),
                'pwdlastset': generate_timestamp(current_time),
                'serviceprincipalnames': generate_client_service_pricipal_names(comp_name),
                'unconstraineddelegation': unconstrained_delegation,
                'privesc': privesc,
                'creddump': creddump,
                'exploitable': exploitable
            }
        }
        props.append(computer_property)
        computer_properties_list.append(computer_property)
        ridcount += 1
 
        if (len(props) > buffer_threshold):
            session.run(
                """
                UNWIND $props as prop
                MERGE (n:Base {objectid: prop.id})
                SET n:Computer, n += prop.props
                WITH n
                MERGE (m:Group {name:$gname})
                WITH n,m
                MERGE (n)-[:MemberOf {isacl:false}]->(m)
                """,
                props=props,
                gname=group_name
            )
            props = []
    session.run(
        """
        UNWIND $props as prop
        MERGE (n:Base {objectid:prop.id})
        SET n:Computer, n += prop.props
        WITH n
        MERGE (m:Group {name:$gname})
        WITH n,m
        MERGE (n)-[:MemberOf {isacl:false}]->(m)
        """,
        props=props,
        gname=group_name
    )
    return computer_properties_list, computers, ridcount, PAW, Server, Workingstation
 


def generate_dcs(session, domain_name, domain_sid, domain_dn, num_nodes, dcou, ridcount, current_time, parameters, functional_level):
    dc_properties_list = []
    ou_dn = get_ou_dn("Domain Controllers", domain_dn)
    enabled_perc = get_perc_param_value("DC", "enabled", parameters)
    has_laps_perc = get_perc_param_value("DC", "haslaps", parameters)
    os_perc = get_dict_param_value("DC", "osProbability", parameters)
    os_list = get_server_os_list(os_perc)

    # New params
    privesc_perc = get_perc_param_value("Computer", "privesc", parameters)
    creddump_perc = get_perc_param_value("Computer", "creddump", parameters)
    exploitable_perc = get_perc_param_value("Computer", "exploitable", parameters)

    print_dc_generation_parameters(enabled_perc, has_laps_perc, os_perc)
    dc_properties_list, ridcount = generate_main_dc(session, domain_name, domain_sid, domain_dn, dcou, ridcount, current_time, parameters, dc_properties_list, functional_level)
    states = STATES[0:num_nodes]
    for state in states:
        comp_name = get_computer_name(f"{state}LABDC", domain_name)
        group_name = get_name("DOMAIN CONTROLLERS", domain_name)
        sid = get_sid_from_rid(ridcount, domain_sid)
        enabled = generate_boolean_value(enabled_perc, get_complementary_value(enabled_perc))
        has_laps = generate_boolean_value(has_laps_perc, get_complementary_value(has_laps_perc))
        os = random.choice(os_list)

        # New params
        privesc = generate_boolean_value(privesc_perc, get_complementary_value(privesc_perc))
        creddump = generate_boolean_value(creddump_perc, get_complementary_value(creddump_perc))
        if is_os_vulnerable(os):
            exploitable = generate_boolean_value(exploitable_perc, get_complementary_value(exploitable_perc))
        else:
            exploitable = False

        dc_properties = {
            'name': comp_name,
            'id': sid,
            'operatingsystem': os,
            'enabled': enabled,
            'haslaps': has_laps,
            'highvalue': False,
            'lastlogontimestamp': generate_timestamp(current_time),
            'pwdlastset': generate_timestamp(current_time),
            'serviceprincipalnames': generate_server_service_pricipal_names(comp_name, domain_name),
            'unconstraineddelegation': True,
            'privesc': privesc,
            'creddump': creddump,
            'exploitable': exploitable
        }
        ridcount += 1
        dc_properties_list.append(dc_properties)
        session.run("""
            MERGE (n:Base {objectid:$sid})
            SET n:Computer,n.name=$name, n.operatingsystem=$os, n.enabled=$enabled, n.haslaps=$haslaps,
            n.highvalue=$highvalue, n.lastlogontimestamp=$lastlogontimestamp, n.pwdlastset=$pwdlastset,
            n.serviceprincipalnames=$serviceprincipalnames, n.unconstraineddelegation=$unconstraineddelegation,
            n.privesc=$privesc, n.creddump=$creddump, n.exploitable=$exploitable
            WITH n MATCH (m:Group {name:$gname})
            WITH n,m
            MERGE (n)-[:MemberOf {isacl:false}]->(m)
            """,
            sid=sid,
            name=comp_name,
            gname=group_name,
            os=dc_properties["operatingsystem"],
            enabled=dc_properties["enabled"],
            haslaps=dc_properties["haslaps"],
            highvalue=dc_properties["highvalue"],
            lastlogontimestamp=dc_properties["lastlogontimestamp"],
            pwdlastset=dc_properties["pwdlastset"],
            serviceprincipalnames=dc_properties["serviceprincipalnames"],
            unconstraineddelegation=dc_properties["unconstraineddelegation"],
            privesc=dc_properties["privesc"],
            creddump=dc_properties["creddump"],
            exploitable=dc_properties["exploitable"]
        )
        set_computer_dn(session, comp_name, ou_dn)
        session.run('MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:OU {objectid:$dcou}) WITH n,m MERGE (m)-[:Contains {isacl:false}]->(n)', sid=sid, dcou=dcou)
        session.run('MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf {isacl:false}]->(m)', sid=sid, gname=get_name("ENTERPRISE DOMAIN CONTROLLERS", domain_name))
        session.run('MERGE (n:Computer {objectid:$sid}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:AdminTo {isacl:false, fromgpo:false}]->(n)', sid=sid, gname=get_name("DOMAIN ADMINS", domain_name))
    return dc_properties_list, ridcount


def generate_main_dc(session, domain_name, domain_sid, domain_dn, dcou, ridcount, current_time, parameters, dc_properties_list, functional_level):
    ou_dn = get_ou_dn("Domain Controllers", domain_dn)
    comp_name = get_computer_name("MAINDC", domain_name)
    group_name = get_name("DOMAIN CONTROLLERS", domain_name)
    sid = get_sid_from_rid(ridcount, domain_sid)
    has_laps_perc = get_perc_param_value("DC", "haslaps", parameters)
    has_laps = generate_boolean_value(has_laps_perc, get_complementary_value(has_laps_perc))

    # New params
    privesc_perc = get_perc_param_value("Computer", "privesc", parameters)
    creddump_perc = get_perc_param_value("Computer", "creddump", parameters)
    exploitable_perc = get_perc_param_value("Computer", "exploitable", parameters)
    privesc = generate_boolean_value(privesc_perc, get_complementary_value(privesc_perc))
    creddump = generate_boolean_value(creddump_perc, get_complementary_value(creddump_perc))
    exploitable = generate_boolean_value(exploitable_perc, get_complementary_value(exploitable_perc))

    dc_properties = {
        'name': comp_name,
        'id': sid,
        'operatingsystem': get_main_dc_os(functional_level),
        'enabled': True,
        'haslaps': has_laps,
        'highvalue': False,
        'lastlogontimestamp': generate_timestamp(current_time),
        'pwdlastset': generate_timestamp(current_time),
        'serviceprincipalnames': generate_server_service_pricipal_names(comp_name, domain_name),
        'unconstraineddelegation': True,
        'privesc': privesc,
        'creddump': creddump,
        'exploitable': exploitable
    }
    ridcount += 1
    dc_properties_list.append(dc_properties)
    session.run("""
        MERGE (n:Base {objectid:$sid})
        SET n:Computer,n.name=$name, n.operatingsystem=$os, n.enabled=$enabled, n.haslaps=$haslaps,
        n.highvalue=$highvalue, n.lastlogontimestamp=$lastlogontimestamp, n.pwdlastset=$pwdlastset,
        n.serviceprincipalnames=$serviceprincipalnames, n.unconstraineddelegation=$unconstraineddelegation,
        n.privesc=$privesc, n.creddump=$creddump, n.exploitable=$exploitable
        WITH n MATCH (m:Group {name:$gname})
        WITH n,m
        MERGE (n)-[:MemberOf {isacl:false}]->(m)
        """,
        sid=sid,
        name=comp_name,
        gname=group_name,
        os=dc_properties["operatingsystem"],
        enabled=dc_properties["enabled"],
        haslaps=dc_properties["haslaps"],
        highvalue=dc_properties["highvalue"],
        lastlogontimestamp=dc_properties["lastlogontimestamp"],
        pwdlastset=dc_properties["pwdlastset"],
        serviceprincipalnames=dc_properties["serviceprincipalnames"],
        unconstraineddelegation=dc_properties["unconstraineddelegation"],
        privesc=dc_properties["privesc"],
        creddump=dc_properties["creddump"],
        exploitable=dc_properties["exploitable"]
    )
    set_computer_dn(session, comp_name, ou_dn)
    session.run('MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:OU {objectid:$dcou}) WITH n,m MERGE (m)-[:Contains {isacl:false}]->(n)', sid=sid, dcou=dcou)
    session.run('MATCH (n:Computer {objectid:$sid}) WITH n MATCH (m:Group {name:$gname}) WITH n,m MERGE (n)-[:MemberOf {isacl:false}]->(m)', sid=sid, gname=get_name("ENTERPRISE DOMAIN CONTROLLERS", domain_name))
    session.run('MERGE (n:Computer {objectid:$sid}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:AdminTo {isacl:false, fromgpo:false}]->(n)', sid=sid, gname=get_name("DOMAIN ADMINS", domain_name))
    return dc_properties_list, ridcount


def generate_default_admin_to(session, domain_sid):
    session.run('MATCH (n:Computer) MATCH (m:Group {objectid: $id}) MERGE (m)-[:AdminTo {isacl:false, fromgpo:false}]->(n)', id=get_sid_from_rid(512, domain_sid))

def get_tiered_objects_2(T0_users, T1_users, T2_users, T0_PAW, T1_PAW, T2_PAW, T0_Server, T1_Server, T2_Server, T0_Workstation, T1_Workstation, T2_Workstation, T0_group, T1_group, T2_group):
	T0_users_arr = T0_users
	T1_users_arr = T1_users
	T2_users_arr = T2_users
	T0_PAW_arr = T0_PAW
	T1_PAW_arr = T1_PAW
	T2_PAW_arr = T2_PAW
	T0_Server_arr = T0_Server
	T1_Server_arr = T1_Server
	T2_Server_arr = T2_Server
	T0_Workstation_arr = T0_Workstation
	T1_Workstation_arr = T1_Workstation
	T2_Workstation_arr = T2_Workstation
	T0_group_arr = T0_group
	T1_group_arr = T1_group
	T2_group_arr = T2_group

def generate_can_rdp_relationships_on_it_users(session, computers, it_users, count):
    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(it_users)
        # props.append({'a': user, 'b': comp})
        if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_users_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_users_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_users_arr))):
        	props.append({'a': user, 'b': comp})

    session.run('UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanRDP {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_can_ps_remote_relationships_on_it_users(session, computers, it_users, count):
    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(it_users)
        # props.append({'a': user, 'b': comp})
        if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_users_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_users_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_users_arr))):
            props.append({'a': user, 'b': comp})

    session.run('UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanPSRemote {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_dcom_relationships_on_it_users(session, computers, it_users, count):
    props = []
    for i in range(0, count):
        comp = random.choice(computers)
        user = random.choice(it_users)
        # props.append({'a': user, 'b': comp})
        if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_users_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_users_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_users_arr))):
            props.append({'a': user, 'b': comp})

    session.run('UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ExecuteDCOM {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_can_rdp_relationships_on_it_groups(session, computers, it_groups, count):
    props = []
    for i in range(0, count):
        try:
            comp = random.choice(computers)
            user = random.choice(it_groups)
            # props.append({'a': user, 'b': comp})
            if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_group_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_group_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_group_arr))):
                props.append({'a': user, 'b': comp})
        except IndexError:
            pass

    session.run('UNWIND $props AS prop MERGE (n:Group {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanRDP {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_can_ps_remote_relationships_on_it_groups(session, computers, it_groups, count):
    props = []
    for i in range(0, count):
        try:
            comp = random.choice(computers)
            user = random.choice(it_groups)
            # props.append({'a': user, 'b': comp})
            if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_group_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_group_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_group_arr))):
                props.append({'a': user, 'b': comp})
        except IndexError:
            pass

    session.run('UNWIND $props AS prop MERGE (n:Group {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:CanPSRemote {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_dcom_relationships_on_it_groups(session, computers, it_groups, count):
    props = []
    for i in range(0, count):
        try:
            comp = random.choice(computers)
            user = random.choice(it_groups)
            # props.append({'a': user, 'b': comp})
            if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_group_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_group_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_group_arr))):
            	props.append({'a': user, 'b': comp})
        except IndexError:
            pass

    session.run('UNWIND $props AS prop MERGE (n:Group {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:ExecuteDCOM {isacl:false, fromgpo:false}]->(m)', props=props)


def generate_allowed_to_delegate_relationships_on_it_users(session, computers, it_users, count):
    props = []
    for i in range(0, count):
        try:
            comp = random.choice(computers)
            user = random.choice(it_users)
            # props.append({'a': user, 'b': comp})
            if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and (user in T0_users_arr)) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and (user in T1_users_arr)) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and (user in T2_users_arr))):
                props.append({'a': user, 'b': comp})
        except IndexError:
            pass

    session.run('UNWIND $props AS prop MERGE (n:User {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:AllowedToDelegate {isacl:false}]->(m)', props=props)


def generate_allowed_to_delegate_relationships_on_computers(session, computers, count):
    props = []
    for i in range(0, count):
        try:
            comp = random.choice(computers)
            user = random.choice(computers)
            if (comp == user):
                continue
            # props.append({'a': user, 'b': comp})
            if ((((comp in T0_PAW_arr) or (comp in T0_Server_arr) or (comp in T0_Workstation_arr)) and ((user in T0_PAW_arr) or (user in T0_Server_arr) or (user in T0_Workstation_arr))) or (((comp in T1_PAW_arr) or (comp in T1_Server_arr) or (comp in T1_Workstation_arr)) and ((user in T1_PAW_arr) or (user in T1_Server_arr) or (user in T1_Workstation_arr))) or (((comp in T2_PAW_arr) or (comp in T2_Server_arr) or (comp in T2_Workstation_arr)) and ((user in T2_PAW_arr) or (user in T2_Server_arr) or (user in T2_Workstation_arr)))):
                props.append({'a': user, 'b': comp})
        except IndexError:
            pass
            
    session.run('UNWIND $props AS prop MERGE (n:Computer {name: prop.a}) MERGE (m:Computer {name: prop.b}) MERGE (n)-[r:AllowedToDelegate {isacl:false}]->(m)', props=props)


def generate_sessions(level, session, num_users, normal_users, Workingstation, Server, T0_users, T1_users, T2_users, T0_PAW,T1_PAW,T2_PAW):
    print("Adding sessions")
    #tiered logon
    max_sessions_per_user = int(math.ceil(math.log10(num_users)))
    props = []
    for user in normal_users:
        num_sessions = random.randrange(0, max_sessions_per_user)

        if num_sessions == 0:
            continue

        for c in random.sample(Workingstation, num_sessions):
            props.append({'a': user, 'b': c})

        if (len(props) > buffer_threshold):
            session.run(
                'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
            props = []

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

    for user in T1_users:
        num_sessions = random.randrange(0, max_sessions_per_user)
        if num_sessions == 0:
            continue

        for c in random.sample(Server, num_sessions):
            props.append({'a': user, 'b': c})

        if (len(props) > buffer_threshold):
            session.run(
                'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
            props = []

    session.run(
        'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

    #PAW logon
    T_users = [T0_users,T1_users,T2_users]
    T_PAW = [T0_PAW,T1_PAW,T2_PAW]
    
    for i in range(3):
        props = []
        for user in T_users[i]:
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue

            for c in random.sample(T_PAW[i], min(num_sessions, len(T_PAW[i]))):
                props.append({'a': user, 'b': c})

            if (len(props) > buffer_threshold):
                session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                props = []

        session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

    if level == 'Medium':
        #create cross tier log on
        cross_tier_up_perc = DEFAULT_VALUES["Cross_Tier_Up"]["Medium"]
        for user in random.sample(normal_users,int(len(normal_users)*cross_tier_up_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(Server+T_PAW, min(num_sessions, len(Server+T_PAW))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
        
        for user in random.sample(T1_users,int(len(T1_users)*cross_tier_up_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(T0_PAW, min(num_sessions, len(T0_PAW))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

        cross_tier_down_perc = DEFAULT_VALUES["Cross_Tier_Down"]["Medium"]
        for user in random.sample(T0_users,int(len(T0_users)*cross_tier_down_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(Workingstation, min(num_sessions, len(Workingstation))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

    elif level == 'High':
        cross_tier_up_perc = DEFAULT_VALUES["Cross_Tier_Up"]["High"]
        for user in random.sample(normal_users,int(len(normal_users)*cross_tier_up_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(Server+T_PAW, min(num_sessions, len(Server+T_PAW))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
        
        for user in random.sample(T1_users,int(len(T1_users)*cross_tier_up_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(T0_PAW, min(num_sessions, len(T0_PAW))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)

        cross_tier_down_perc = DEFAULT_VALUES["Cross_Tier_Down"]["High"]
        for user in random.sample(T0_users,int(len(T0_users)*cross_tier_down_perc)):
            num_sessions = random.randrange(0, max_sessions_per_user)
            if num_sessions == 0:
                continue
            for c in random.sample(Workingstation, min(num_sessions, len(Workingstation))):
                props.append({'a': user, 'b': c})

                if (len(props) > buffer_threshold):
                    session.run(
                    'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)
                    props = []

            session.run(
            'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Computer {name:prop.b}) WITH n,m MERGE (m)-[:HasSession]->(n)', props=props)




def assign_unconstrained_delegation(session, computers):
    i = random.randint(10, 20)
    i = min(i, len(computers))
    for computer in random.sample(computers, i):
        session.run('MATCH (n:Computer {name:$computer}) SET n.unconstrainteddelegation=true', computer=computer)


def set_computer_dn(session, computer_name, ou_dn):
    computer_dn = get_computer_dn(computer_name, ou_dn)
    query = "MATCH (n:Computer { name: '" + computer_name + "' }) SET n.distinguishedname = '" + computer_dn + "' RETURN n.name, n.distinguishedname"
    session.run(query)
