import random
import math
from adsimulator.entities.groups import get_forest_default_groups_list, get_forest_default_group_members_list
from adsimulator.templates.groups import get_departments_list
from adsimulator.utils.principals import get_sid_from_rid, get_name
from adsimulator.utils.groups import get_group_dn, generate_group_description
from adsimulator.utils.boolean import generate_boolean_value
from adsimulator.templates.default_values import get_complementary_value
from adsimulator.utils.parameters import get_dict_param_value, print_departments_parameters
from adsimulator.templates.ous import STATES
from adsimulator.templates.groups import DEPARTMENTS_LIST
from adsimulator.templates.default_values import DEFAULT_VALUES

buffer_threshold = DEFAULT_VALUES["Buffer_Threshold"]


T0_users_arr = []
T1_users_arr = []
T2_users_arr = []
T0_group_arr = []
T1_group_arr = []
T2_group_arr = []

def generate_default_groups(session, domain_name, domain_sid, old_domain_name):
    default_groups_list = get_forest_default_groups_list(domain_name, domain_sid, old_domain_name)
    for default_group in default_groups_list:
        try:
            session.run(
                """
                MERGE (n:Base {name: $gname}) SET n:Group, n.objectid=$sid,
                n.highvalue=$highvalue, n.domain=$domain,
                n.distinguishedname=$distinguishedname,
                n.description=$description, n.admincount=$admincount
                """,
                gname=default_group["Properties"]["name"],
                sid=default_group["ObjectIdentifier"],
                highvalue=default_group["Properties"]["highvalue"],
                domain=default_group["Properties"]["domain"],
                distinguishedname=default_group["Properties"]["distinguishedname"],
                description=default_group["Properties"]["description"],
                admincount=default_group["Properties"]["admincount"]
            )
        except KeyError:
            default_group_properties = default_group["Properties"]
            if not "highvalue" in default_group_properties:
                highvalue = "null"
            else:
                highvalue = default_group["Properties"]["highvalue"]
            if not "distinguishedname" in default_group_properties:
                dn = "null"
            else:
                dn = default_group["Properties"]["distinguishedname"]
            if not "description" in default_group_properties:
                description = "null"
            else:
                description = default_group["Properties"]["description"]
            if not "admincount" in default_group_properties:
                admincount = "null"
            else:
                admincount = default_group["Properties"]["admincount"]
            if not "domain" in default_group_properties:
                domain = "null"
            else:
                domain = default_group["Properties"]["domain"]
            
            session.run(
                """
                MERGE (n:Base {name: $gname}) SET n:Group, n.objectid=$sid,
                n.highvalue=$highvalue, n.domain=$domain,
                n.distinguishedname=$distinguishedname,
                n.description=$description, n.admincount=$admincount
                """,
                gname=default_group["Properties"]["name"],
                sid=default_group["ObjectIdentifier"],
                highvalue=highvalue,
                domain=domain,
                distinguishedname=dn,
                description=description,
                admincount=admincount
            )


def generate_groups(session, domain_name, domain_sid, domain_dn, num_groups, groups, ridcount, parameters):

    depart = ['IT','HR','MARKETING','OPERATIONS','BIDNESS']
    props =[]
    group_properties_list = []
    # Distribution Groups
    for i in depart:
        group_name = get_name(i+'_'+'dist', domain_name)
        sid = get_sid_from_rid(ridcount,domain_sid)
        ridcount += 1
        groups.append(group_name)
        group_properties = {
            'name': group_name,
            'id': sid,
            'dn': get_group_dn(group_name, domain_dn),
            'admincount': False,
            'description': generate_group_description(group_name),
            'highvalue': False
        }
        props.append(group_properties)
        group_properties_list.append(group_properties)

        session.run('UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
        for j in STATES:
            sub_dist = get_name(i+'_'+j, domain_name)
            sid = get_sid_from_rid(ridcount,domain_sid)
            ridcount += 1

            groups.append(sub_dist)

            group_properties = {
                'name': sub_dist,
                'id': sid,
                'dn': get_group_dn(group_name, domain_dn),
                'admincount': False,
                'description': generate_group_description(group_name),
                'highvalue': False
            }
            props.append(group_properties)
            group_properties_list.append(group_properties)

            session.run(
                'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
            session.run(
                'MERGE (n:Group {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=group_name, gname=get_name('Distribution Groups',domain_name))
            session.run(
                'MERGE (n:Group {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:MemberOf]->(n)', gname=sub_dist, name=group_name)



    # Security Groups
    ACL = ['Read','Modify','Write','Full']
    folder_name = ['Folder_' + str(i) for i in range(1,6) ]
    for i in depart:
        group_name = get_name(i+'_'+'sec', domain_name)
        sid = get_sid_from_rid(ridcount,domain_sid)
        ridcount += 1
        groups.append(group_name)
        group_properties = {
            'name': group_name,
            'id': sid,
            'dn': get_group_dn(group_name, domain_dn),
            'admincount': False,
            'description': generate_group_description(group_name),
            'highvalue': False
        }
        props.append(group_properties)
        group_properties_list.append(group_properties)

        session.run(
            'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
        for l in ACL:
            for n in range(random.randint(0, 5)):
                sub_sec = get_name(i+'_'+folder_name[n]+'_'+l, domain_name)
                sid = get_sid_from_rid(ridcount,domain_sid)
                ridcount += 1
                groups.append(sub_sec)
                group_properties = {
                    'name': sub_sec,
                    'id': sid,
                    'dn': get_group_dn(group_name, domain_dn),
                    'admincount': False,
                    'description': generate_group_description(group_name),
                    'highvalue': False
                }
                props.append(group_properties)
                group_properties_list.append(group_properties)

                session.run(
                    'UNWIND $props as prop MERGE (n:Base {objectid:prop.id}) SET n:Group, n.name=prop.name', props=props)
                session.run(
                    'MERGE (n:Group {name:$name}) WITH n MERGE (m:OU {name:$gname}) WITH n,m MERGE (m)-[:Contains]->(n)', name=group_name, gname=get_name('Security Groups',domain_name))
                session.run(
                    'MERGE (n:Group {name:$name}) WITH n MERGE (m:Group {name:$gname}) WITH n,m MERGE (m)-[:MemberOf]->(n)', gname=sub_sec, name=group_name)



    return group_properties_list, groups, ridcount


def generate_domain_administrators(session, domain_name, num_nodes, users):
    dapctint = random.randint(3, 5)
    dapct = float(dapctint) / 100
    danum = int(math.ceil(num_nodes * dapct))
    danum = min([danum, 30])
    print("Generating {} Domain Admins ({}% of users capped at 30)".format(danum, dapctint))
    das = random.sample(users, danum)
    for da in das:
        session.run(
            """
            MERGE (n:User {name:$name})
            WITH n
            MERGE (m:Group {name:$gname})
            WITH n,m
            MERGE (n)-[:MemberOf {isacl:false}]->(m)
            SET n.admincount = true
            """,
            name=da,
            gname=get_name("DOMAIN ADMINS", domain_name))
    return das


def generate_default_member_of(session, domain_name, domain_sid, old_domain_name):
    standard_group_members_list = get_forest_default_group_members_list(domain_name, domain_sid, old_domain_name)
    for group_member in standard_group_members_list:
        add_member_of_relationship(session, group_member)


def add_member_of_relationship(session, ad_object):
    query = "MATCH (memberItem:" + ad_object["MemberType"] + " {objectid: '" + ad_object["MemberId"] + "'}), (groupItem:Group {objectid: '" + ad_object["GroupId"] + "'})"
    query = query + "\nMERGE (memberItem)-[:MemberOf {isacl:false}]->(groupItem)"
    session.run(query)


def nest_groups(session, num_nodes, groups, nesting_perc):
    max_nest = int(round(math.log10(num_nodes)))
    props = []
    for group in groups:
        if generate_boolean_value(nesting_perc, get_complementary_value(nesting_perc)):
            try:
                num_nest = random.randrange(1, max_nest)
            except ValueError:
                num_nest = 1
            dept = group[0:-19]
            dpt_groups = [x for x in groups if dept in x]
            if num_nest > len(dpt_groups):
                num_nest = random.randrange(1, len(dpt_groups))
            to_nest = random.sample(dpt_groups, num_nest)
            for g in to_nest:
                if not g == group:
                    props.append({'a': group, 'b': g})

        if (len(props) > buffer_threshold):
            session.run('UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf {isacl:false}]->(m)', props=props)
            props = []

    session.run('UNWIND $props AS prop MERGE (n:Group {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf {isacl:false}]->(m)', props=props)


def get_tiered_objects_1(T0_users, T1_users, T2_users, T0_group, T1_group, T2_group):
    T0_users_arr = T0_users
    T1_users_arr = T1_users
    T2_users_arr = T2_users
    T0_group_arr = T0_group
    T1_group_arr = T1_group
    T2_group_arr = T2_group

def assign_users_to_group(session, normal_users, das, domain_name):
    it_users = []
    for user in normal_users:
        dept = random.choice(DEPARTMENTS_LIST)
        if dept == "IT":
            it_users.append(user)
        session.run('MATCH (n:User {name:$name}) SET n.department = $dept_name', name=user, dept_name = dept)
        query = session.run('MATCH(n:Group)-[:MemberOf]->(o:Group{name:$uname}) RETURN n.name',uname = get_name(dept+'_'+'dist', domain_name)).data()
        dist_group = [list(i.values())[0] for i in query]
        possible_dist = random.choices(dist_group)
        query = session.run('MATCH(n:Group)-[:MemberOf]->(o:Group{name:$uname}) RETURN n.name',uname = get_name(dept+'_'+'sec', domain_name)).data()
        sec_group = [list(i.values())[0] for i in query]
        possible_groups = possible_dist + random.sample(sec_group,random.randint(0, len(sec_group)))
        for group in possible_groups:
            props =[]
            # props.append({'a': user, 'b': group})
            if ((user in T0_users_arr) and (group in T0_group_arr)) or ((user in T1_users_arr) and (group in T1_group_arr)) or ((user in T2_users_arr) and (group in T2_group_arr)):
                props.append({'a': user, 'b': group})
            session.run(
                'UNWIND $props AS prop MERGE (n:User {name:prop.a}) WITH n,prop MERGE (m:Group {name:prop.b}) WITH n,m MERGE (n)-[:MemberOf]->(m)', props=props)
 

    it_users = it_users + das
    it_users = list(set(it_users))
    return it_users, dist_group, sec_group
