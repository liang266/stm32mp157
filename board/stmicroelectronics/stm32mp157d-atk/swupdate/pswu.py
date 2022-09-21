#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Author  : xieyongbin
# @Time    : 2021/6/21
# @Function:
import os
import re
import sys
import argparse
import json
import hashlib
import functools
from jsonlibconfig import encoder
from jsonlibconfig import decoder

ras_key_create = False
clean_before_exit = False
debug_enable = False
out_path = ""


def check_files(cfg, img, files):
    """
    check config specify file can read
    :param cfg: global json config
    :param img: an imges config
    :param files: files list
    :return: all files found return True, otherwise return False
    """
    no_found_list = []
    # remove same filename
    path = "/".join([cfg["rootpath"], cfg["images_path"]])
    # cmd = f"rm -rf {path}/*.enc"
    # if debug_enable:
    #     print(f"check_files: cmd is {cmd}")
    # os.system(cmd)
    for f in list(set(files["common"])):
        # .enc suffix ?
        if os.path.splitext(f)[-1] == ".enc":
            # basename
            f = os.path.splitext(f)[0]
        if not os.access("/".join([path, f]), os.R_OK):
            # file not found
            no_found_list.append("/".join([path, f]))

    path = "/".join([cfg["rootpath"], img["swupdate"]["path"]])
    for f in list(set(files["custom"])):
        # .enc suffix ?
        if os.path.splitext(f)[-1] == ".enc":
            # basename
            f = os.path.splitext(f)[0]
        if not os.access("/".join([path, f]), os.R_OK):
            # file not found
            no_found_list.append("/".join([path, f]))

    if len(no_found_list):
        # enable compress?
        if cfg["tgz_compress"] or cfg["gz_compress"]:
            # remove a list should copy list avoid wrong
            for f in no_found_list[:]:
                # get basename and suffix
                basename, suffix = os.path.splitext(f)
                # not support .tar.gz
                if suffix == ".tgz" and cfg["tgz_compress"]:
                    if os.access(basename, os.R_OK):
                        # os return 0 for success, but python value 0 is False
                        # option -h deal with symbol link
                        if not os.system(f"tar czfh {f} {basename}"):
                            no_found_list.remove(f)

                elif suffix == ".gz" and cfg["gz_compress"]:
                    if os.access(basename, os.R_OK):
                        # option -f deal with symbol link
                        if not os.system(f"gzip -k -f {basename}"):
                            no_found_list.remove(f)

    if len(no_found_list):
        # enable compress?
        print(f"Error: for images {img} follow files can not found:")
        for f in no_found_list:
            print(f"\t{f}")
        return False

    return True


def get_software_versions(filename="sw-versions"):
    """
    get real software versions from specify file
    :param filename: save real software versions
    :return: success return version dict, otherwise return None
    """
    version = {}
    try:
        f = open(filename)
    except FileNotFoundError:
        print(f"Error: can not found {filename}")
        return None
    else:
        lines = f.readlines()
        f.close()
        for line in lines:
            # return a list
            c = line.split()
            if len(c) != 2:
                print(f"Error: {c} format not correct")
                return False
            else:
                version[c[0]] = c[1]
        return version


def get_release_versions(filename="issue"):
    """
    get real software versions from specify file
    :param filename: save real software versions
    :return: release version for success, or None for failure
    """
    try:
        f = open(filename)
    except FileNotFoundError:
        print(f"Error: can not found {filename}")
        return None
    else:
        line = f.readline()
        f.close()
        return line.strip()


def fill_software_versions(one_image, versions):
    """
    replace json real software versions.
    if real versions not exsit specify software version, use "UNKOWN" instend of
    :param json: json template for an image
    :param versions: real software versions
    """
    t = type(one_image["images"]).__name__
    if t == "list":
        for img in one_image["images"]:
            if not len(img):
                continue
            if "version" in img.keys():
                # set real versions to json
                v = img["version"]
                if v in versions.keys():
                    img["version"] = versions[v]
                else:
                    img["version"] = "UNKOWN"
    elif t == "dict":
        img = one_image["images"]
        if "version" in img.keys():
            # set real versions to json
            v = img["version"]

            if v in versions.keys():
                img["version"] = versions[v]
            else:
                img["version"] = "UNKOWN"


def sha256sum(filename):
    try:
        with open(filename, "rb") as f:
            d = hashlib.sha256()
            # read 4M bytes one time
            for buf in iter(functools.partial(f.read, 0x400000), b""):
                d.update(buf)
            return d.hexdigest()
    except Exception as e:
        print(f"Error: sha256sum open {filename} error {e}")
        return None


def enc_one_image(filename, key, iv):
    cmd = f'''openssl enc -aes-256-cbc -in {filename} -out {filename}.enc -K {key} -iv {iv}'''
    if debug_enable:
        print(f'enc_one_image: cmd is {cmd}')
    return os.system(cmd)


def fill_enc_rsa(path, files, key, iv):
    """
    replace json real software versions.
    if real versions not exsit specify software version, use "UNKOWN" instend of
    :param j: json from user provide libconfig config file
    """
    t = type(files).__name__
    if t == "list":
        for img in files:
            if not len(img):
                continue
            if "encrypted" in img.keys():
                if img["encrypted"]:
                    filename = "/".join([path, img["filename"]])
                    # enc the image context
                    enc_one_image(filename, key, iv)
                    # replace "filename" at sw-description"
                    # remove file_list
                    img["filename"] = img["filename"] + ".enc"
                    img["ivt"] = iv

            if "sha256" in img.keys():
                filename = "/".join([path, img["filename"]])
                sha256 = sha256sum(filename)
                if not sha256:
                    continue
                if debug_enable:
                    print(f'fill_enc_rsa: file {filename} sha256sum is {sha256}')
                # replace origin sha256sum
                img["sha256"] = sha256
    elif t == "dict":
        img = files
        # enc the image context
        if "encrypted" in img.keys():
            if img["encrypted"]:
                filename = "/".join([path, img["filename"]])
                enc_one_image(filename, key, iv)
                # replace "filename" at sw-description"
                img["filename"] = img["filename"] + ".enc"
                img["ivt"] = iv

        if "sha256" in img.keys():
            filename = "/".join([path, img["filename"]])
            sha256 = sha256sum(filename)
            if not sha256:
                return None
            if debug_enable:
                print(f'fill_enc_rsa: file {filename} sha256sum is {sha256}')
            img["sha256"] = sha256

    return True


def parse_libconfig_to_json(filename):
    """
    parse user provide config file, only support libconfig language now
    :param filename: template libconfig file name
    :return: failed return None, otherwise return json format converted by @filename
    """
    try:
        with open(filename) as f:
            context = f.read()
    except Exception as e:
        print(f"Error: file {filename} open {e}")
        return None
    else:
        try:
            # libconfig to json
            json = decoder.loads(context)
        except Exception as e:
            print(f"Error: decoder {filename} error {e}")
            return None
        else:
            return json


def get_image_files_from_json(one_image):
    """
    Get files name that specified.
    The files location root images path(default "./images_path") as key "common" value
    The files location image custom path(img["swupdate"]["path"]) as key "custom" value
    :param json: json template format
    :return: the list contains files name
    """
    files = {}
    if "images" in one_image.keys():
        t = type(one_image["images"]).__name__
        if t == "list":
            for img in one_image["images"]:
                # I found he last item end with "comma" in file description libconfig key "images",
                # after conver to json, json end with a empty list [] that cause
                # "AttributeError: 'list' object has no attribute 'keys'"
                # check the len of list to avoid
                if not len(img):
                    continue
                if "filename" in img.keys():
                    suffix = ""
                    # get key "files", if not exist set it
                    if "encrypted" in img.keys():
                        if img["encrypted"]:
                            suffix = ".enc"
                    files.setdefault("common", []).append(img["filename"] + suffix)
        elif t == "dict":
            if "filename" in one_image["images"].keys():
                suffix = ""
                # get key "files", if not exist set it
                if "encrypted" in one_image["images"].keys():
                    if one_image["images"]["encrypted"]:
                        suffix = ".enc"
                files.setdefault("common", []).append(one_image["images"]["filename"] + suffix)

    if "files" in one_image.keys():
        t = type(one_image["files"]).__name__
        if t == "list":
            for img in one_image["files"]:
                if not len(img):
                    continue
                if "filename" in img.keys():
                    suffix = ""
                    if "encrypted" in img.keys():
                        if img["encrypted"]:
                            suffix = ".enc"
                    files.setdefault("common", []).append(img["filename"] + suffix)
        elif t == "dict":
            if "filename" in one_image["files"].keys():
                suffix = ""
                if "encrypted" in one_image["files"].keys():
                    if one_image["files"]["encrypted"]:
                        suffix = ".enc"
                files.setdefault("common", []).append(one_image["files"]["filename"] + suffix)

    if "scripts" in one_image.keys():
        t = type(one_image["scripts"]).__name__
        if t == "list":
            for img in one_image["scripts"]:
                if not len(img):
                    continue
                if "filename" in img.keys():
                    suffix = ""
                    if "encrypted" in img.keys():
                        if img["encrypted"]:
                            suffix = ".enc"
                    files.setdefault("custom", []).append(img["filename"] + suffix)
        elif t == "dist":
            if "filename" in one_image["scripts"].keys():
                suffix = ""
                if "encrypted" in one_image["scripts"].keys():
                    if one_image["encrypted"]:
                        suffix = ".enc"
                files.setdefault("custom", []).append(one_image["scripts"]["filename"] + suffix)

    return files


def generage_swupdate_config(j, files, out="sw-description"):
    """
    convert json to libconfig
    :param j: the context will write
    :param files: files name list that will pack into .swu packages
    :param out: output file, defualt "sw-description"
    :return: success return True, otherwise return False
    """
    libconfig = encoder.dumps(j, 4)
    try:
        with open(out, "w") as f:
            f.write(libconfig)
            # keep same use relative path
            files["custom"].append(os.path.basename(out))
            return True
    except Exception as e:
        print(f"Error: write {out} {e}")
        return False


def generage_swu_package(cfg, img, files, name):
    """
    pack .swu package for swupdate
    :param cfg: json config
    :param img: an image config(table)
    :param files: @img list files that package into .swu
    :param name: output .swu package
    :return: success return True, otherwise return False
    """
    fs = []

    common_path = "/".join([cfg["rootpath"], cfg["images_path"]])
    custom_path = "/".join([cfg["rootpath"], img["swupdate"]["path"]])

    # common files
    for i in range(len(files["common"])):
        fs.append("/".join([common_path, files["common"][i]]))

    # custom files
    for i in range(len(files["custom"])):
        fs.append("/".join([custom_path, files["custom"][i]]))
    # remove same files
    fs = list(set(fs))

    sw_description_sig_path = "/".join([custom_path, "sw-description.sig"])
    if sw_description_sig_path in fs:
        # promise file 'sw-description.sig' locate the sencond item that swupdate requires
        fs.remove(sw_description_sig_path)
        fs.insert(0, sw_description_sig_path)

    sw_description_path = "/".join([custom_path, "sw-description"])
    if sw_description_path not in fs:
        return False
    # promise file 'sw-description' exist and locate the first item that swupdate requires
    fs.remove(sw_description_path)
    fs.insert(0, sw_description_path)

    # the swupdate only support relative path, use symbol link avoid cause error
    fs_symbol_link = []
    for f in fs:
        symbol_name = os.path.basename(f)
        if os.path.exists(symbol_name):
            try:
                os.unlink(symbol_name)
            except Exception as e:
                print(f"Error: unlink file {symbol_name} {e}")
        os.symlink(f, symbol_name)
        fs_symbol_link.append(symbol_name)

    if debug_enable:
        print(f"file list: {fs_symbol_link}")
    # files list to string
    fs_str = " ".join(fs_symbol_link)
    # quiet output and do not print files, the most important is use origin file
    cmd = f'''for f in {fs_str}; do echo $f; done |  cpio -o -H crc -L --quiet > {name}'''
    ret = not os.system(cmd)
    # clean symbol link file
    for f in fs_symbol_link:
        try:
            os.unlink(f)
        except Exception as e:
            print(f"Error: unlink file {f} {e}")
    return ret


def generage_signature_file(filename, priv_filename, passwd):
    """
    signature the outfile, normal "sw-description" to "sw-description.sig"
    :param filename: in filename
    :param priv_filename private key filename
    :param passwd: private password
    :return:
    """
    cmd = f'''openssl dgst -sha256 -passin pass:{passwd} -sign {priv_filename} {filename} > {filename}.sig'''
    return os.system(cmd)


def handle_one_swu_package(cfg, pkg):
    """
    handle one image:
    1. collect the image require files
    2. check 1st require files exist?
    3. get real release_version and replace json
    4. generate libconfig format "sw-description" that for swupdate
    5. generate .swu package that for swupdate
    :param cfg: global json config(table)
    :param pkg: an image config(table)
    :return: True for success, or False for failure
    """
    pkg_desc = {}

    # libconfig filename that is a template, we convert the template file to end libconfig file that parsed by swupdate
    if "inconfig" not in pkg["swupdate"]:
        libconfig_template = "/".join([cfg["rootpath"], pkg["swupdate"]["path"], "description"])
    else:
        libconfig_template = "/".join([cfg["rootpath"], pkg["swupdate"]["path"], pkg["swupdate"]["inconfig"]])

    # check if provide out file name(default "swupdate"/"path"/sw-description)
    if "outconfig" not in pkg["swupdate"]:
        libconfig_filename = "/".join([cfg["rootpath"], pkg["swupdate"]["path"], "sw-description"])
    else:
        libconfig_filename = "/".join([cfg["rootpath"], pkg["swupdate"]["path"], pkg["swupdate"]["outconfig"]])

    # convert libconfig template to json template that easier to parse
    json_template = parse_libconfig_to_json(libconfig_template)
    if json_template is None:
        return False

    images_nodes = find_images_keys(json_template)

    pkg_desc["files"] = handle_swu_package_images_node(cfg, pkg, json_template, images_nodes)

    if not generage_swupdate_config(json_template, pkg_desc["files"], libconfig_filename):
        return False

    if "encrypted" in cfg["rsa"].keys():
        if cfg["rsa"]["encrypted"]:
            generage_signature_file(libconfig_filename, cfg["rsa"]["priv_filename"], cfg["rsa"]["passwd"])
            pkg_desc["files"]["custom"].append("sw-description.sig")

    swu_filename = pkg["name"] + "_" + cfg["release_version"] + ".swu"
    # boolean type, keep package name same with property "name" when set
    if "raw_name" in pkg.keys() and pkg["raw_name"]:
        swu_filename = pkg["name"] + ".swu"

    # specify output path?
    if len(out_path):
        swu_filename = "/".join([out_path, swu_filename])
    if debug_enable:
        print(f"swu out path: {swu_filename}")

    if not generage_swu_package(cfg, pkg, pkg_desc["files"], swu_filename):
        print(f"Error: generage swu package {swu_filename}")
        return False

    print(f"generage package {swu_filename} success\n")
    return True


def parse_cmdline_encrypt(cfg):
    """
    parse cmdline for symmetric-key algorithm
    :param cfg: global json config(table)
    :return: True for success, otherwise None
    """
    # promise cfg["enc"]["encrypted"] exist that as condition whether symmetric-key algorithm
    if "enc" not in cfg.keys():
        cfg["enc"] = {"encrypted": False}
    else:
        if "encrypted" in cfg["enc"].keys() and cfg["enc"]["encrypted"]:
            if "passwd" not in cfg["enc"].keys() or "salt" not in cfg["enc"].keys():
                print("Error: Key 'passwd' and 'salt' should exist at 'enc'")
                return None
            # get "key" and "iv" through "passwd" and "salt"
            cmd = f'''openssl enc -aes-256-cbc -k {cfg["enc"]["passwd"]} -pbkdf2 -S {cfg["enc"]["salt"]} -P'''
            if debug_enable:
                print(f'enc cmd {cmd}')
            f = os.popen(cmd)
            if not f:
                return None
            for l in f.readlines():
                # TODO: re module deal the result
                obj = re.match(r'(.*)=(.*)', l, re.I)
                if obj:
                    # salt=6A4179C10F0C6476
                    # obj.group(1).strip() = "salt"
                    # obj.group(1).strip() = 6A4179C10F0C6476
                    # c["enc"]["salt"] = "6A4179C10F0C6476"
                    if debug_enable:
                        print(f'enc {obj.group(1).strip()}: {obj.group(2).strip()}')
                    cfg["enc"][obj.group(1).strip()] = obj.group(2).strip()

            if ras_key_create:
                key_name = "key"
                if len(out_path):
                    key_name = "/".join([out_path, key_name])
                key_iv = cfg["enc"]["key"] + " " + cfg["enc"]["iv"]
                with open(key_name, "w") as f:
                    f.write(key_iv)

    return True


def parse_cmdline_rsa(cfg):
    """
    parse cmdline for asymmetric key encryption
    :param cfg: global json config(table)
    :return: True for success, otherwise None
    """
    if "rsa" not in cfg.keys():
        cfg["rsa"] = {"encrypted": False}
    else:
        if debug_enable:
            print(f'rsa passwd: {cfg["rsa"]["passwd"]}')
        if "encrypted" in cfg["rsa"].keys() and cfg["rsa"]["encrypted"] and ras_key_create:
            if "passwd" not in cfg["rsa"].keys() or "priv_filename" not in cfg["rsa"].keys():
                print("Error: Key 'passwd' and 'priv_filename' should exist at 'ras'")
                return None
            priv_name = "priv.pem"
            public_name = "public.pem"
            if len(out_path):
                priv_name = "/".join([out_path, priv_name])
                public_name = "/".join([out_path, public_name])

            # private key
            # TODO: subprocess replacement os.system
            cmd = f'''openssl genrsa -aes256 -passout pass:{cfg["rsa"]["passwd"]} -out {priv_name}'''
            os.system(cmd)
            # public key
            cmd = f'''openssl rsa -in {priv_name} -out {public_name} -outform PEM -pubout -passin pass:{cfg["rsa"]["passwd"]}'''
            os.system(cmd)

            # use new create key file
            cfg["rsa"]["priv_filename"] = priv_name

    return True


def parse_swu_package_fullname(cfg):
    """
    parse cmdline for swu package fullname
    :param cfg: global json config(table)
    :return: True for success, otherwise None
    """
    # release version that join into .swu name
    if "release_version" in cfg.keys():
        path = "/".join([cfg["rootpath"], cfg["images_path"], cfg["release_version"]])
        release_version = get_release_versions(path)
        if release_version is None:
            print(f"Error: release version can not parse from {path}")
            return None
        cfg["release_version"] = release_version
    else:
        cfg["release_version"] = ""
    if debug_enable:
        print(f'relase versions: {cfg["release_version"]}')

    return True


def parse_real_softwares_version(cfg):
    """
    get real softwares version
    :param cfg: global json config(table)
    :return: True for success, otherwise None
    """
    path = "/".join([cfg["rootpath"], cfg["images_path"], cfg["software_versions"]])
    software_versions = get_software_versions(path)
    if software_versions is None:
        print(f"Error: software versions can not parse from {path}")
        return None
    cfg["software_versions"] = software_versions
    if debug_enable:
        print(f'real software versions: {cfg["software_versions"]}')

    return True


def check_cmdline_configs(cfg):
    """
    Global property:
        require keys:
            "software_versions": real software filename
            "images": images config, see "The images section"
        option keys:
            "rootpath": the work root path, default current work directory
            "images_path": the common images path that all common images locations, default "rootpath"/images
            "release_version": release version path
            "tgz_compress": boolean type, if "images_path" not exist "filename.tgz" file but exist "filename",
                compress it automatic to "filename.tgz"
            "gz_compress": boolean type, if "images_path" not exist "filename.gz" file but exist "filename",
                compress it automatic to "filename.gz"
            "enc": symmetric-key algorithm description, see "The enc section"
            "rsa": asymmetric key encryption description, see "The rsa section"

    "images" child property:
        require keys:
            "name": name of .swu package.
                If property "raw_name" is True, package name is "name".swu.
                otherwise "name"_"release_version".swu
            "swupdate": image custom config
                require keys:
                    "path": image custom directory path
                option keys:
                    # "raw_name": boolean type, keep package name same with property "name" when set
                    "inconfig": the swupdate libconfig that contain mostly config except software version,
                        default "description"
                    "outconfig": the swupdate libconfig that contain all config, maybe same as "inconfig",
                        default "sw-description"

    "enc" child property:
        require keys:
            "passwd": the password for encrypt image context.
            "salt": the salt for encrypt image context
        option keys:
            "encrypted": boolean type, enable symmetric-key algorithm, default False

    "rsa" child property:
        require keys:
            "passwd": the password for encrypt image context.
            "priv_filename": the private key for signature "sw-description" file
        option keys:
            "encrypted": boolean type, enable asymmetric key encryption, default False

    :param cfg: json config
    :return: True for success, otherwise None
    """
    if "images" not in cfg or "software_versions" not in cfg:
        print("Error: property 'images' and 'software_versions' required")
        return None
    # check every image necessary keys, only support list and dict
    images_type = type(cfg["images"]).__name__
    if images_type == "list":
        for image in cfg["images"]:
            if "name" not in image or "swupdate" not in image or "path" not in image["swupdate"]:
                print("Error: lost necessary keys")
                return None
    elif images_type == "dict":
        if "name" not in cfg["images"] or "swupdate" not in cfg["images"] or "path" not in cfg["images"]["swupdate"]:
            print("Error: lost necessary keys")
            return None
    else:
        print("Error: Key 'images' should a list or dict")
        return None

    if "rootpath" not in cfg:
        cfg["rootpath"] = os.getcwd()
    if "images_path" not in cfg:
        cfg["images_path"] = "images"

    if "tgz_compress" not in cfg:
        cfg["tgz_compress"] = False
    if "gz_compress" not in cfg:
        cfg["gz_compress"] = False

    # TODO: deal follow function return
    # openssl enc
    parse_cmdline_encrypt(cfg)

    # openssl rsa
    parse_cmdline_rsa(cfg)

    # release version that join into .swu name
    parse_swu_package_fullname(cfg)

    # get real software version
    parse_real_softwares_version(cfg)

    return True


def parse_cmdline_args():
    """
    parse cmdline line
    :return: success return config dict, otherwise return {}
    """
    parse = argparse.ArgumentParser(description="A tool for generate swupdate package .swu")
    parse.add_argument("config", default="config.json", help="json file for top config")
    parse.add_argument("-c", "--clean", action="store_true", help="enable clean temporary files before exit")
    parse.add_argument("-k", "--key", action="store_true", help="create rsa public and private key")
    parse.add_argument("-o", "--output", default="", help="swu pakcage output path")
    parse.add_argument("-d", "--debug", action="store_true", help="enable debug info")
    parse.add_argument("-v", "--version", action="version", version="1.0.0")
    args = parse.parse_args()

    # use global var
    global ras_key_create, clean_before_exit, debug_enable, out_path
    debug_enable = args.debug
    out_path = args.output
    ras_key_create = args.key
    clean_before_exit = args.clean

    try:
        with open(args.config, "r") as f:
            context = f.read()
    except Exception as e:
        print(f"Error: open {args.config} {e}")
        return {}
    else:
        try:
            cfg = json.loads(context)
        except Exception as e:
            print(f"Error: load config file {args.config} to json {e}")
            return {}
        else:
            err = check_cmdline_configs(cfg)
            if not err:
                return {}
            return cfg


def find_images_keys(json):
    """
    swupdate find "images" follow below priority
    1. <boardname>.<selection>.<mode>.<entry>
    2. <selection>.<mode>.<entry>
    3. <boardname>.<entry>
    4. <entry>

    - the "<selection>.<mode>" passed by cmdline
    - "<entry>" normal is "images"
    :json: json template for an image
    :return: the paths of "images node"
    """
    nodes = []
    # for key in ["images", "files", "scripts"]:
    for key in ["images"]:
        result = foreach_specify_field_keys(json, [key])
        if len(result):
            nodes.append(result)

    return nodes


def foreach_specify_field_keys(data, fields=None, cur_key=None):
    """
    foreach a json template for a swu package, find out the specify key @cur_key path
    :param data: a list or a dict
    :param fields: a list contains key that filter out
    :param cur_key: current key
    :return: the list contains values of key @cur_key
    """
    if fields is None:
        fields = []

    result = []

    if isinstance(data, dict):
        for k, v in data.items():
            if k in fields:
                # print(f"foreach_specify_field dict: {cur_key} {fields} {type}")
                result.append(cur_key)
                return result
            ret = foreach_specify_field_keys(v, fields, k)
            # we can not return immediately avoid to lost rest "key" entry
            for r in ret:
                if cur_key:
                    result.append(" ".join([cur_key, r]))
                else:
                    result.append(r)
    return result


def handle_swu_package_images_node(cfg, pkg, json, images_nodes):
    """
    handle images node that define in one sw-description file.
    in double copy mode, one sw-description file may exist more than one images node
    :param cfg: global json config(table)
    :param pkg: an images config(table)
    :return: an images node contain files
    """
    for node in images_nodes:
        for k in node:
            images_node = json
            for k1 in str.split(k):
                images_node = images_node[k1]

            # the files that location "rootpath/images_path" or "rootpath/swupdate/path"
            files_list = get_image_files_from_json(images_node)

            # empty dict?
            if len(files_list) == 0:
                print("Error: no files provide")
                return False

            if not check_files(cfg, pkg, files_list):
                return False

            fill_software_versions(images_node, cfg["software_versions"])

            # fill "files" "scripts" and "images" sha256 and iv keys
            # Note: "files" and "scripts" are option
            if "files" in images_node.keys():
                fill_enc_rsa("/".join([cfg["rootpath"], cfg["images_path"]]), images_node["files"],
                             cfg["enc"]["key"], cfg["enc"]["iv"])

            if "scripts" in images_node.keys():
                fill_enc_rsa("/".join([cfg["rootpath"], pkg["swupdate"]["path"]]), images_node["scripts"],
                             cfg["enc"]["key"], cfg["enc"]["iv"])

            if "images" in images_node.keys():
                fill_enc_rsa("/".join([cfg["rootpath"], cfg["images_path"]]), images_node["images"],
                             cfg["enc"]["key"], cfg["enc"]["iv"])

    return files_list


def main():
    cfg = parse_cmdline_args()
    if len(cfg) == 0:
        sys.exit(-1)

    # list or dist?
    pkg_type = type(cfg["images"]).__name__
    if pkg_type == "list":
        for pkg in cfg["images"]:
            if not len(pkg):
                continue
            # it shoud create some thread to handle?
            handle_one_swu_package(cfg, pkg)
    elif pkg_type == "dict":
        handle_one_swu_package(cfg, cfg["images"])
    else:
        pass


if __name__ == "__main__":
    main()
