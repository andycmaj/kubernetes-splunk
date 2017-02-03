import os
import sys
import json
import time
import socket
import re
import glob
import subprocess
from shutil import move
from zipfile import ZipFile
from urllib import urlretrieve
from tempfile import mktemp

import requests

import splunk.clilib.cli_common
import splunk.util


var_expandvars_re = re.compile(r'\A\ENV\((.*)\)$')
var_shell_re = re.compile(r'\ASHELL\((.*)\)$')


def main():
    """
    Initialize node. Can run before splunk started and after splunk started
    """
    if sys.argv[1] == "--configure":
        print "configuring splunk..."
        configure(sys.argv[2])
    elif sys.argv[1] == "--restore-config":
        print "restoring splunk config..."
        restore_config()
    elif sys.argv[1] == "--wait-splunk":
        print "waiting for other splunk roles..."
        wait_splunk(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "--add-licenses":
        add_licenses(sys.argv[2])
    elif sys.argv[1] == "--shc-autobootstrap":
        shc_autobootstrap(int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8])
    else:
        exit(1)


def configure(conf_file_path):
    """
    using CONF__ notation you can define any configuration, examples
    CONF__[{location_under_splunk_home}__]{conf_file}__{stanza}__{key}=value
    If location_under_splunk_home is not specified - system is used.
    """
    # Allow to set any configurations with this
    conf_updates = {}
    with open(conf_file_path) as conf_file:
        for env, val in dict(line.split('=') for line in conf_file).iteritems():
            if env.startswith("CONF__"):
                parts = env.split("__")[1:]
                conf_file_name = None
                parent = None
                conf_folder = "system"
                if len(parts) == 4:
                    conf_folder = parts[0]
                    parts = parts[1:]
                conf_folder_full = __get_conf_folder_full(conf_folder, parent)
                file_name = parts[0]
                if file_name == "meta":
                    file_name = "local.meta"
                    subfolder = "metadata"
                else:
                    file_name = file_name + ".conf"
                    subfolder = "local"
                conf_file = os.path.join(conf_folder_full, subfolder, file_name)
                val = __get_value(val)
                conf_updates.setdefault(conf_file, {}).setdefault(parts[1], {})[parts[2]] = val
                print "({}) {}:{} -> {}".format(conf_file, parts[1], parts[2], val)
    for conf_file, conf_update in conf_updates.iteritems():
        conf = splunk.clilib.cli_common.readConfFile(conf_file) if os.path.exists(conf_file) else {}
        for stanza, values in conf_update.iteritems():
            dest_stanza = conf.setdefault(stanza, {})
            dest_stanza.update(values)
        if "default" in conf and not conf["default"]:
            del conf["default"]
        folder = os.path.dirname(conf_file)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        splunk.clilib.cli_common.writeConfFile(conf_file, conf)


def restore_config():
    """
    restore backed up cluster-master configuration before starting splunk for the first time
    """
    zip_url_format = os.path.expandvars("$REPO_ZIP_URL_FORMAT")
    zip_filename = os.path.expandvars("$REPO_ZIP_FILENAME")
    dest_dir = os.path.expandvars("$CONFIG_RESTORE_PARENT")
    if not zip_filename or zip_filename == "$REPO_ZIP_FILENAME":
        print "No config backup to restore."
        return
    zip_url = zip_url_format.format(zip_filename)
    print "Restoring config backup from {}".format(zip_url)
    temp_filename = mktemp('.zip')
    try:
        name, hdrs = urlretrieve(zip_url, temp_filename)
        print "downloaded {}".format(temp_filename)
        archive = ZipFile(temp_filename)
        archive.extractall(dest_dir)
        archive.close()
        print "extracted zip to {}".format(dest_dir)
        restore_from = os.path.join(dest_dir, 'etc')
        print "copying from {}".format(restore_from)
        subprocess.call("cp -rf {} {}".format(restore_from, '/opt/splunk'), shell=True)
        print "Restored config to {}".format(dest_dir)
    except IOError as e:
        print "Error restoring config. I/O error({0}): {1}".format(e.errno, e.strerror)
    except:
        print "Error restoring config:", sys.exc_info()[0]


def __get_value(val):
    print "get value: {}".format(val)

    var_expand_match = var_expandvars_re.match(val)
    if var_expand_match:
        env_var_name = var_expand_match.groups()[0]
        env_var_value = os.path.expandvars(env_var_name)
        print "val {} is an environment var. value: {}".format(env_var_name, env_var_value)
        return env_var_value
    var_shell_match = var_shell_re.match(val)
    if var_shell_match:
        return subprocess.check_output(var_expand_match.groups()[0], shell=True)
    return val


def __get_conf_folder_full(conf_folder, parent):
    if conf_folder == "system":
        return os.path.join(os.environ["SPLUNK_HOME"], "etc", conf_folder)
    else:
        return os.path.join(os.environ["SPLUNK_HOME"], conf_folder)


def wait_splunk(uri, roles):
    """
    Wait 5 minutes for dependency
    """
    print "waiting for {} to be available".format(uri)
    for x in xrange(1, 600):
        try:
            # This url does not require authentication, ignore certificate
            response = requests.get(uri + "/services/server/info?output_mode=json", verify=False)
            if response.status_code == 200:
                server_roles = response.json()["entry"][0]["content"]["server_roles"]
                if not roles or all(any(re.match(role, server_role) for server_role in server_roles) for role in roles):
                    return
                else:
                    print "Waiting for " + ", ".join(roles) + " in " + uri + " got " + ", ".join(server_roles) + "."
            else:
                print "Waiting for "+ ", ".join(roles) + " in " + uri + "."
        except requests.exceptions.RequestException as exception:
            print "Waiting for " + ", ".join(roles) + " in " + uri + ". Exception: " + str(exception)
        time.sleep(1)
    print "Failed to connect to " + uri + " and check server roles " + ", ".join(roles)
    exit(1)


def add_licenses(folder):
    while True:
        if os.path.isdir(folder):
            licenses = glob.glob(os.path.join(folder, "*.lic"))
            if licenses:
                # Adding all licenses one by one and break
                for license in licenses:
                    args = [
                        "add",
                        "licenses",
                        "-auth", "admin:changeme",
                        license
                    ]
                    __splunk_execute(args)
                break

        print "Waiting for license files under " + folder
        time.sleep(1)


def shc_autobootstrap(autobootstrap, mgmt_uri, local_user, local_password, service_discovery_uri, service_discovery_user, service_discovery_password):
    """
    Write current uri to the service discovery URL, if current member has index equal
    to INIT_SHCLUSTER_AUTOBOOTSTRAP - bootstrap SHC, if more - add itself to existing SHC
    """
    __service_discovery_post(service_discovery_uri, service_discovery_user, service_discovery_password, data=json.dumps({"host": mgmt_uri}), headers={"Content-type": "application/json"})
    all_members = __service_discovery_get(service_discovery_uri, service_discovery_user, service_discovery_password, params={"sort": "_key"}).json()
    for index, member in enumerate(all_members):
        if member["host"] == mgmt_uri:
            if (index + 1) == autobootstrap:
                print "Bootstrapping " + mgmt_uri + " as shc captain"
                __splunk_execute([
                    "bootstrap",
                    "shcluster-captain",
                    "-auth", "%s:%s" % (local_user, local_password),
                    "-servers_list", ",".join(m["host"] for m in all_members[:autobootstrap])
                ])
            elif (index + 1) > autobootstrap:
                # We do not check if current list of members already bootstrapped, assuming that autobootstrap is always equal to
                # how many instances user creating at beginning
                __splunk_execute([
                    "add",
                    "shcluster-member",
                    "-auth", "%s:%s" % (local_user, local_password),
                    "-current_member_uri", next(m["host"] for m in all_members[:autobootstrap])
                ])


def __service_discovery_get(service_discovery_uri, service_discovery_user, service_discovery_password, **kwargs):
    for x in xrange(1, 600):

        try:
            response = requests.get(service_discovery_uri,
                                    verify=False,
                                    auth=(service_discovery_user, service_discovery_password),
                                    **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as ex:
            print "Failed to make GET request to service discovery url. " + str(ex)
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(1)
    print "FAILED. Could not make GET request to service discovery url."
    exit(1)


def __service_discovery_post(service_discovery_uri, service_discovery_user, service_discovery_password, **kwargs):
    for x in xrange(1, 600):
        try:
            response = requests.post(service_discovery_uri,
                                     verify=False,
                                     auth=(service_discovery_user, service_discovery_password),
                                     **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as ex:
            print "Failed to make POST request to service discovery url. " + str(ex)
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(1)
    print "FAILED. Could not make POST request to service discovery url."
    exit(1)


def __splunk_execute(args):
    """
    Execute splunk with arguments
    """
    sys.stdout.flush()
    sys.stderr.flush()
    splunk_args = [os.path.join(os.environ['SPLUNK_HOME'], "bin", "splunk")]
    splunk_args.extend(args)
    subprocess.check_call(splunk_args)
    sys.stdout.flush()
    sys.stderr.flush()


if __name__ == "__main__":
    main()
