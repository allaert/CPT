#!/usr/bin/env python3

#    CPT 0.5.0

#    CPT - provides a gui to flash the ubports project to the all stable
#    devices. It started out as a tool to flash the Fairphone 2
#    Copyright (C) 2017  Smoose B.V. - Allaert Euser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
# 
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import namedtuple

# Create Device to be used with devices
Device = namedtuple('Device', 'name friendly recovery boot channels status')
# Add core devices
fp2 = Device(name='FP2', friendly='Fairphone 2', 
    recovery='http://ci.ubports.com/job/daily-fp2/lastSuccessfulBuild/artifact/device_FP2_devel.tar.xz', 
    boot='', channels=('stable', 'rc', 'devel'),  status='Core')
hammerhead = Device(name='hammerhead', friendly='Nexus 5',
    recovery='http://ci.ubports.com/view/all/job/daily-hammerhead/lastSuccessfulBuild/artifact/device_hammerhead_devel.tar.xz', 
    boot='', channels=('stable', 'rc', 'devel'), status='Core')
bacon = Device(name='bacon', friendly='OnePlus One', 
    recovery='http://ci.ubports.com/view/all/job/daily-bacon/lastSuccessfulBuild/artifact/device_bacon_devel.tar.xz', 
    boot='', channels=('stable', 'rc', 'devel'), status='Core')


all_devices = [ fp2, hammerhead, bacon ]
