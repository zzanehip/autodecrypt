#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import logging
import os
import shutil
import sys
import zipfile
from remotezip import RemoteZip
from optparse import OptionParser

import decrypt_img
from scrapkeys import KeyGrabber
from ipsw_dl import IpswDownloader


logging.basicConfig(filename="my_deployer.log",
					format='%(asctime)s %(message)s',
					datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)

def grab_file(url, filename):
	with RemoteZip(url) as zip:
		filenames = zip.namelist()
		for fname in filenames:
			zinfo = zip.getinfo(fname)
			if filename in zinfo.filename and not ".plist" in zinfo.filename:
				filename = zinfo.filename.split("/")[-1]
				print("[i] downloading %s" % filename)
				extract_and_clean(zip, zinfo.filename, filename)
				return filename
		return filename

def extract_and_clean(zipper, zip_path, filename):
	zipper.extract(zip_path)
	if "/" in zip_path :
		os.rename(zip_path, filename)
		shutil.rmtree(zip_path.split('/')[0])

image_types = [
	["ogol", "logo", "applelogo"],
	["0ghc", "chg0", "batterycharging0"],
	["1ghc", "chg1", "batterycharging1"],
	["Ftab", "batF", "Ftab"],
	["Ftab", "batF", "batteryfull"],
	["0tab", "bat0", "batterylow0"],
	["1tab", "bat1", "batterylow1"],
	["ertd", "dtre", "devicetree"],
	["Cylg", "glyC", "glyphcharging"],
	["Pylg", "glyP", "glyphplugin"],
	["tobi", "ibot", "iboot"],
	["blli", "illb", "llb"],
	["ssbi", "ibss", "ibss"],
	["cebi", "ibec", "ibec"],
	["lnrk", "krnl", "kernelcache"],
	["sepi", "sepi", "sepfirmware"]
]

def get_image_type_name(image):
	image = image.decode("utf-8")
	for i in range(0, len(image_types)):
		if image == image_types[i][0] or image == image_types[i][1]:
			img_type = image_types[i][2]
			return img_type
	return None


def parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file",  required=True, dest="img_file", help="img file you want to decrypt")
	parser.add_argument("-d","--device", required=True, dest="device", help="device ID  (eg : iPhone8,1)")
	parser.add_argument("-i","--ios", dest="ios_version", help="iOS version for the said file")
	parser.add_argument("-b","--build", dest="build_id", help="build ID to set instead of iOS version")
	parser.add_argument("-c","--codename", dest="codename", help="codename of iOS version")
	parser.add_argument("-l","--local", action='store_true', help="don't download firmware image")
	parser.add_argument("--beta", action='store_true', help="specify beta version")

	return parser.parse_args()

def main():
	argv = sys.argv
	argc = len(argv)
	set_ios_version = False

	build = None
	codename = None
	ios_version = None

	parser = parse_arguments()
	logging.info('Launching "{}"'.format(*sys.argv))

	if parser.ios_version is not None:
		ios_version = parser.ios_version

	if parser.build_id is not None:
		build = parser.build_id

	scrapkeys = KeyGrabber()

	if parser.beta is not True:
		if parser.ios_version is not None:
			build = scrapkeys.version_or_build(parser.device, ios_version, build)
		else:
			ios_version = scrapkeys.version_or_build(parser.device, ios_version, build)

	if parser.codename is None:
		codename = scrapkeys.get_codename(parser.device, ios_version, build)

	if parser.local is not True:
		ipsw = IpswDownloader()
		ipsw_url = ipsw.parse_json(parser.device, ios_version, build, parser.beta)[0]

		parser.img_file = grab_file(ipsw_url, parser.img_file)

	url = "https://www.theiphonewiki.com/wiki/" + codename + "_" + build + "_" + "(" + parser.device + ")"

	magic, image_type = decrypt_img.get_image_type(parser.img_file)
	image_name = get_image_type_name(image_type)

	if image_name is None:
		print("[e] image type not found")

	print("[i] image : %s" % image_name)
	print("[i] grabbing keys from %s" % url)
	image_keys = scrapkeys.parse_iphonewiki(url, image_name)

	iv = image_keys[:32]
	key = image_keys[-64:]
	print("[x] iv  : %s" % iv)
	print("[x] key : %s" % key)

	decrypt_img.decrypt_img(parser.img_file, parser.img_file + ".dec", magic, key, iv, openssl='openssl')
	print("[x] done")

if __name__ == '__main__':
	main()
