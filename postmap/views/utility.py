#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  postmap/views/utility.py
#

import string
from random import choice
import re
import numpy as np
from datetime import datetime, timedelta, timezone
import logging
import gpxpy
from postmap.views.gps_utils import haversine

from bs4 import BeautifulSoup as bs
from io import BytesIO

# Import image libraries
from PIL import Image as pImage
from PIL import UnidentifiedImageError
from PIL import ExifTags
import base64
# Folium map imports
import folium
from folium.plugins import MeasureControl, FloatImage, MarkerCluster
from folium import features, IFrame
import branca.colormap as cm

from postmap import app
from postmap import db
from postmap.models.tables import Image, Track, Result
from flask import flash, session

#==================
# Utility functions
#==================

def check_database(timeout):
	# delete rows in db table which were
	#created more than timeout seconds ago
	images = Image.query
	tracks = Track.query
	results = Result.query
	for img in images:
		delta = datetime.utcnow()-img.time
		if delta.total_seconds() > timeout:
			logging.debug(f'Old image detected, created {delta.seconds}s ago')
			db.session.delete(img)
			
	for trk in tracks:
		delta = datetime.utcnow()-trk.time
		if delta.total_seconds() > timeout:
			logging.debug(f'Old track detected, created {delta.seconds}s ago')
			db.session.delete(trk)
	for res in results:
		delta = datetime.utcnow()-res.time
		if delta.total_seconds() > timeout:
			logging.debug(f'Old results detected, created {delta.seconds}s ago')
			db.session.delete(res)
	db.session.commit()
	return 0

def add_layers(my_map):
	'''
	Add layers to a folium map.
	'''
	#folium.TileLayer('Stamen Terrain').add_to(my_map)
	#folium.TileLayer(tiles='https://tiles.nakarte.me/map_podm/{z}/{x}/{y}', 
	#             attr='nakarte.me', name='Slazav Map', tms=True).add_to(my_map)
	folium.TileLayer(tiles='https://a.tile.opentopomap.org/{z}/{x}/{y}.png',
				attr='<a href="https://opentopomap.org/" target="_blank">OpenTopoMap</a>', 
				name='OpenTopo Map', default=True).add_to(my_map)
	folium.TileLayer(tiles='https://maps.refuges.info/hiking/{z}/{x}/{y}.png',
				attr='<a href="https://maps.refuges.info/" target="_blank">Refuges Info</a>', 
				name='Maps.Refuges.Info').add_to(my_map)
	#folium.TileLayer(tiles='http://a.tiles.wmflabs.org/hikebike/{z}/{x}/{y}.png',
	#            attr='OpenStreetMap', name='Hike-bike OSM').add_to(my_map)
	folium.TileLayer(tiles='http://slazav.xyz/tiles/podm/{x}-{y}-{z}.png',
				attr='<a href="http://slazav.xyz/maps" target="_blank">Vladislav Zavjalov</a>', 
				name='Slazav podm', maxNativeZoom=13).add_to(my_map)
	folium.TileLayer(tiles='http://slazav.xyz/tiles/hr/{x}-{y}-{z}.png',
				attr='<a href="http://slazav.xyz/maps" target="_blank">Vladislav Zavjalov</a>', 
				name='Slazav mountains', maxNativeZoom=13).add_to(my_map)
	folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
				attr='<a href="https://www.google.com/maps/" target="_blank">Google</a>', 
				name='Google Satellite').add_to(my_map)
	folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}',
				attr='<a href="https://www.google.com/maps/" target="_blank">Google</a>', 
				name='Google Terrain').add_to(my_map)
	folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
				attr='<a href="https://www.google.com/maps/" target="_blank">Google</a>', 
				name='Google Hybrid').add_to(my_map)
	# folium.TileLayer(tiles='https://mapserver.mapy.cz/turist-m/{z}-{x}-{y}',
				# attr='Mapy.cz', name='Mapy.cz - tourist').add_to(my_map)
	folium.TileLayer(tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
				attr='<a href="https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9" target="_blank">ESRI World Imagery for ArcGIS</a>', 
				name='Esri Satellite').add_to(my_map)
	
	#folium.TileLayer(tiles='https://mapserver.mapy.cz/bing/{z}-{x}-{y}',
	#            attr='Mapy.cz', name='Mapy.cz - satellite').add_to(my_map)
#https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}
#http://mt.google.com/vt/lyrs=s&amp;x=%2&amp;y=%3&amp;z=%1 --google satellite
#http://mt.google.com/vt/lyrs=t&amp;x=%2&amp;y=%3&amp;z=%1 --google terrain

	folium.LayerControl().add_to(my_map)

def get_map_src(html):
	soup = bs(html, 'lxml')
	ifr = soup.find('iframe')
	map_frame = ifr.attrs['srcdoc']
	soup_frame = bs(map_frame, 'lxml')
	map_id = soup_frame.find('div', attrs={'class':'folium-map'}).attrs['id']
	scr = soup_frame.find('script', text=re.compile('L.map'))
	scr.append('{}.attributionControl.setPrefix(\'Created with Folium\');\n'.format(map_id))
	ifr.attrs['srcdoc'] = str(soup_frame)
	return str(soup_frame)

def upload_trk_file(up_file):
	gpx = gpxpy.gpx.GPX()
	fname = up_file.filename
	if fname != '':
		file_ext = fname.rsplit('.', 1)[1].lower()
		if file_ext not in app.config['UPLOAD_EXTENSIONS']:
			flash('Неверное расширение файла', 'bad')
			abort(400)
		try:
			gpx = gpxpy.parse(up_file)
			info = track_info(gpx)
			flash('Файл \"{}\" успешно прочитан'.format(fname), 'good')
			return gpx, info
		except Exception:
			logging.exception('Error while uploading file!')
			#map_view=''
			flash('Неверный формат файла', 'bad')
			return None, None
	else:
		flash('Файл не выбран', 'bad')
		return None, None
	
def trackint_simple(track_line, interval):
	new_index = np.arange(0, len(track_line), interval)
	lat_list = []
	lon_list = []
	new_line = []
	num_list = np.arange(0, len(track_line))
	lat_list=[p[0] for p in track_line]
	lon_list=[p[1] for p in track_line]
	lat_inter = np.interp(new_index, num_list, lat_list)
	lon_inter = np.interp(new_index, num_list, lon_list)
	new_line = list(zip(lat_inter, lon_inter))
	return new_line

def random_string(length):
	#Generate random alphanumeric string with length=length
	letters = string.ascii_letters
	digits = string.digits
	symbols = letters + digits
	return ''.join(choice(symbols) for i in range (length))

def make_line(gpx):
	line=[]
	if len(gpx.tracks)>0:
		for i, p in enumerate(gpx.tracks[0].segments[0].points):
			line.append(tuple([p.latitude, p.longitude]))
	return line
	
def track_to_csv(gpx):
	lines=[]
	lines.append('lat, lon, ele[m], dist[m], time, speed[m/s]')
	try:
		pts = gpx.tracks[0].segments[0].points
	except IndexError:
		pts = []
	length = make_length_list(gpx)[0]
	logging.debug(f'Lenght length = {len(length)}')
	logging.debug(f'Points length = {len(pts)}')
	for i, p in enumerate(pts):
		s=[]
		if p.latitude:
			s.append(str(p.latitude))
		else:
			s.append('NaN')
		if p.longitude:
			s.append(str(p.longitude))
		else:
			s.append('NaN')
		if p.elevation:
			s.append(str(p.elevation))
		else:
			s.append('NaN')
		s.append(str(length[i]))
		if p.time:
			s.append(str(p.time))
		else:
			s.append('NaN')
		if p.speed:
			s.append(str(p.speed))
		else:
			s.append('NaN')
		line = ','.join(s)
		lines.append(line)
	lines = '\n'.join(lines)
	#logging.debug(f'CSV lines: {lines}')
	csv = BytesIO(lines.encode('utf-8'))
	return csv

def wpts_to_csv(gpx):
	lines=[]
	lines.append('name, comment, lat, lon, ele[m], time')
	wpts = [w for w in gpx.waypoints if not w.name=='Точка остановки']
	stops = [w for w in gpx.waypoints if w.name=='Точка остановки']
	for w in wpts:
		s=[]
		if w.name:
			s.append(w.name)
		else:
			s.append('')
		if w.comment:
			s.append(w.comment)
		else:
			s.append('')
		if w.latitude:
			s.append(str(w.latitude))
		else:
			w.append('NaN')
		if w.longitude:
			s.append(str(w.longitude))
		else:
			s.append('NaN')
		if w.elevation:
			s.append(str(w.elevation))
		else:
			s.append('NaN')
		if w.time:
			s.append(str(w.time))
		else:
			s.append('NaN')
		lines.append(','.join(s))
	lines.append('name, t_start, t_end, duration[min], lat, lon, ele[m], time')
	for w in stops:
		s=[]
		s.append(w.name)
		comment = w.comment.replace('Начало: ', '')
		comment = comment.replace('Конец: ', '')
		comment = comment.replace('Продолжительность: ', '')
		comment = comment.replace('UTC', '')
		comment = comment.replace('мин.', '')
		fields = comment.split(',')
		s +=fields
		s +=[str(w.latitude), str(w.longitude), str(w.elevation), str(w.time)]
		lines.append(','.join(s))
	lines = '\n'.join(lines)
	csv = BytesIO(lines.encode('utf-8'))
	return csv
	
def make_speed_colorline(gpx):
	if gpx.has_times():
		line = make_line(gpx)
		try:
			speeds = [p.speed*3.6 for p in gpx.tracks[0].segments[0].points]
		except TypeError:
			return None, None
		color_line = features.ColorLine(
				 positions=line,
				 colors=speeds,
				 colormap=['red', 'yellow', 'green'],
			    weight=5)
		colormap = cm.LinearColormap(['red', 'yellow', 'green'], 
						 vmin=min(speeds),
						 vmax=max(speeds),
						 caption=u'Скорость, км/ч')
		return color_line, colormap
	else:
		return None, None

def add_height(gpx):
	return gpx
	
def proper_time(interval):
	'''
	Converts interval in seconds to (h,m) format
	'''
	h = interval//3600
	m = interval%3600//60
	return h, m
	
def make_length_list(gpx):
	length_list=[]
	try:
		points = [(p.latitude, p.longitude) for p in gpx.tracks[0].segments[0].points]
	except IndexError:
		return length_list, tuple([0, 0])
	l=haversine(points[0], points[1])
	length_list.append(l)
	for i in range(1, len(points)):
		#logging.debug(f'point1={points[i]}, point2={points[i-1]}')
		l +=haversine(points[i], points[i-1])
		length_list.append(l)
	l=[abs(l-length_list[-1]//2) for l in length_list]
	l_min = min(l)
	i=l.index(l_min)
	center = tuple([points[i][0], points[i][1]])
	return length_list, center
	
def make_stats_mark(gpx, name: str, speed_threshold: float):
	if gpx.has_times():
		t_start, t_fin = gpx.get_time_bounds()
		total_hours, total_min = proper_time((t_fin-t_start).total_seconds())
		moving_time, stopped_time, moving_distance, stopped_distance, max_speed = gpx.get_moving_data(speed_threshold)
		mov_time_hours, mov_time_min = proper_time(moving_time)
		try:
			tot_avg_speed = gpx.length_2d()/(t_fin-t_start).total_seconds()*3.6
			tot_mov_speed = moving_distance/moving_time*3.6
		except ZeroDivisionError:
			tot_avg_speed = 0
			tot_mov_speed = 0
		
	else:
		total_hours = 0
		total_min = 0
		mov_time_hours = 0
		mov_time_min = 0
		tot_avg_speed = 0
		tot_mov_speed = 0
	length = gpx.length_2d()/1000
	uphill, downhill = gpx.get_uphill_downhill()
	stats_html=f'''<div style="font-family: courier new; font-size: 150%; color: black">
		<h3>Трек: {name}</h3>
		Протяженность: {length:.1f}км<br>
		Общее время: {total_hours:.0f}ч {total_min:.0f}мин<br>
		Время в движении: {mov_time_hours:.0f}ч {mov_time_min:.0f}мин<br>
		Набор/сброс высоты: {uphill:.0f}/{downhill:.0f}м<br>
		Общая средняя скорость: {tot_avg_speed:.1f}км/ч<br>
		Средняя в движении: {tot_mov_speed:.1f}км/ч<br>
		</div>'''
	length_list, center = make_length_list(gpx)
	stats_popup = folium.Popup(stats_html, max_width=500)
	marker = folium.Marker(location = [center[0], center[1]], popup = stats_popup, 
             icon=folium.Icon(color='red'))
	return marker

	
def find_stops(gpx, threshold: float):
	'''
	Finds stops on track based on speed threshold (in m/s). Returns stops as folium marks
	with stop info as a popup. Also returns DataFrame with stops info organized in a table.
	'''
	if gpx.has_times():
		flag = False
		stop_start = []
		stop_end = []
		stop_lat = []
		stop_lon = []
		stop_ele = []
		temp_i=[]
		duration = []
		stop_points = []
		stop_waypoints=[]
		stop_html =u"""
		Начало остановки: {0} UTC<br>
		Конец остановки: {1} UTC<br>
		Продолжительность: {2:.0f} мин<br>
		""".format
		time_list = [p.time for p in gpx.tracks[0].segments[0].points]
		speed_list = [p.speed for p in gpx.tracks[0].segments[0].points]
		lat_list = [p.latitude for p in gpx.tracks[0].segments[0].points]
		lon_list = [p.longitude for p in gpx.tracks[0].segments[0].points]
		ele_list = [p.elevation for p in gpx.tracks[0].segments[0].points]
		try:
			for i, p in enumerate(gpx.tracks[0].segments[0].points):
				if p.speed < threshold and not flag:
					stop_start.append(p.time)
					flag = True
					temp_i.append(i) 
				elif p.speed >= threshold and flag:
					stop_lat.append(lat_list[temp_i[len(temp_i)//2]])
					stop_lon.append(lon_list[temp_i[len(temp_i)//2]])
					stop_ele.append(ele_list[temp_i[len(temp_i)//2]])
					temp_i=[]
					stop_end.append(p.time)
					flag = False
			if flag:
				stop_lat.append(lat_list[temp_i[len(temp_i)//2]])
				stop_lon.append(lon_list[temp_i[len(temp_i)//2]])
				stop_ele.append(ele_list[temp_i[len(temp_i)//2]])
				stop_end.append(time_list[-1])    
			for i in zip(stop_start, stop_end):
				duration.append((i[1]-i[0]).total_seconds())
			stops_table={'start_time_UTC': stop_start,
									 'end_time_UTC': stop_end,
									 'duration': duration, 
									 'lat': stop_lat, 'lon': stop_lon,
									 'ele': stop_ele}
			for i in range(len(stops_table['duration'])):
				if stops_table['duration'][i] > 120:
					#stop_icon = folium.Icon(icon='flag', color = 'lightblue', icon_color='green', prefix = 'fa')
					mark = folium.Marker(location=[stops_table['lat'][i], 
												stops_table['lon'][i]])
					popup=folium.Popup(stop_html(stops_table['start_time_UTC'][i],
										   stops_table['end_time_UTC'][i],
										   round(stops_table['duration'][i]/60)), max_width=500).add_to(mark)
					stop_points.append(mark)
					stop_waypoints.append(gpxpy.gpx.GPXWaypoint(latitude = stops_table['lat'][i], 
													  longitude = stops_table['lon'][i],
													  elevation = stops_table['ele'][i],
												name =  'Точка остановки',
												comment='Начало: {0} UTC, Конец: {1} UTC, Продолжительность: {2:.1f} мин.'\
												.format(stops_table['start_time_UTC'][i],
												  stops_table['end_time_UTC'][i],
													 stops_table['duration'][i]/60),
												time = stops_table['start_time_UTC'][i]))
			gpx.waypoints += stop_waypoints
		except TypeError:
			return gpx, {}, []
		return gpx, stops_table, stop_points
	else:
		return gpx, {}, []
	
def make_marks(gpx, step):
	# i_coords = mt.trackint_simple(current_track['coords'], 0.2)
	# marks = mt.make_marks(i_coords, float(ops['step'])*1000)
	line = make_line(gpx)
	i_line = trackint_simple(line, 0.2)
	l = 0
	wpts = []
	marks = []
	mark_symbols = []
	html_mark = """
		     <div style="font-family: courier new; font-size: 120%; color: darkgreen; text-shadow: 0 2px 2px white, 0 -2px 2px white, 2px 0 2px white, -2px 0 2px white;">{0}
		       </div>""".format
	length = 0
	for i in range(1, len(i_line)):
		p1 = i_line[i-1]
		p2 = i_line[i]
		length = length + haversine(p1,p2)
		if (length > l):
			name =  '{0:.0f}km'.format(l/1000.0)
			wpts.append(gpxpy.gpx.GPXWaypoint(latitude = p2[0], 
											  longitude = p2[1], 
										name =  name,
										 symbol='Civil'))
			marks.append(folium.Marker(location=[p2[0], p2[1]],
				  icon=folium.DivIcon(html = html_mark(name), icon_anchor=(-10,10))))
			mark_symbols.append(folium.CircleMarker(location = [p2[0], p2[1]], 
                         radius=3, popup=name, opacity=0.8))
			l = l + step
	marked_gpx = gpx
	marked_gpx.waypoints += wpts
	return marked_gpx, marks, mark_symbols

def make_image_points(gpx, offset: int):
	logging.info('Make images call')
	image_markers=[]
	t = None
	lat = None
	lon = None
	if gpx.has_times():
		html = '<img src="data:image/png;base64,{}">'.format
		images = Image.query.filter(Image.user_id==session['user_id']).all()
		images = sorted(images, key=lambda image: image.name)
		#delta = timedelta(hours=offset)
		#gpx.adjust_time(delta, all=True)
		points = gpx.tracks[0].segments[0].points
		i = 0
		for image in images:
			logging.debug(f'Image name: {image.name}')
			if re.search('^img[0-9]{8}-[0-9]{6}\.jpg', image.name.lower()):
				t = datetime(year = int(image.name[3:7]), 
				month = int(image.name[7:9]),
				day = int(image.name[9:11]),
				hour = int(image.name[12:14]),
				minute = int(image.name[14:16]),
				second = int(image.name[16:18]), tzinfo=points[0].time.tzinfo)
				logging.info(f'Image time: {t}')
			elif not image.shoot_time is None:
				t = image.shoot_time
				t = t.replace(tzinfo=points[0].time.tzinfo)
				logging.info(f'Image time: {t}')
			if not t is None:
				hr = t.hour - offset
				if hr>=0:
					t=t.replace(hour = hr)
				else:
					t=t.replace(day = t.day-1, hour = 24+hr)
				while t>points[i].time and i<len(points)-1:
					i += 1
				lat = points[i].latitude
				lon = points[i].longitude
				logging.info(f'Image {image.name} located by time')
				logging.info(f'Image {image.name} location: lat={lat}, lon={lon}')
			elif not image.lat is None and not image.lon is None:
				lat = float(image.lat)
				lon = float(image.lon)
				logging.info(f'Image {image.name} located by geoExif')
			else:
				logging.info(f'Image {image.name} is not located')
			if not lat is None and not lon is None:
				gpx.waypoints.append(gpxpy.gpx.GPXWaypoint(
				latitude = lat, longitude = lon, 
				name =  image.name, symbol='Box, Blue', time = points[i].time,
				comment=f'{points[i].time} UTC'))
				iframe = IFrame(html(image.img), 
					width=image.width*1.02, height=image.height*1.05)
				popup = folium.Popup(iframe, max_width=image.width*1.02)
				image_icon = folium.Icon(icon='camera', color = 'lightgreen', 
							icon_color='white', prefix='fa')
				marker = folium.Marker(location=[lat, lon], 
                            popup=popup, tooltip=f'{points[i].time} UTC', icon=image_icon)
				image_markers.append(marker)
	return gpx, image_markers
		

def make_poi(target_gpx, source_gpx):
	poi=[]
	for wpt in source_gpx.waypoints:
		target_gpx.waypoints.append(wpt)
		mark = folium.Marker(location=[wpt.latitude, 
										wpt.longitude], 
							 icon=folium.Icon(color='orange'), tooltip=wpt.name)
		if not wpt.comment==None:
			popup = folium.Popup(wpt.comment, max_width=500).add_to(mark)
		poi.append(mark)
	return target_gpx, poi
	
def track_info(gpx):
	t = 0
	s = 0
	info_l=[]
	info_l.append('<p><ul>\n')
	for t, track in enumerate(gpx.tracks):
		info_l.append('<li> Трек <b>{}</b><ul>\n'.format(t))
		for s, segment in enumerate(track.segments):
			length = segment.length_2d()
			info_l.append('<li>Cегмент <b>{}</b>, количество точек: <b>{}</b>, \
			длина: <b>{:.1f}</b>км</li>\n'.format(s, len(segment.points), length/1000))
		info_l.append('</ul>')
	info_l.append(f'<li>Путевых точек: <b>{len(gpx.waypoints)}</b></li>\n')
	info_l.append('</ul></p>\n')
	return ''.join(info_l)
	
def draw_map(
	plan_track_line=[], 
	fact_track_line=[], 
	proc_track_line=[],
	color_line=None,
	colormap=None,
	stats_mark=None,
	poi_list=[], 
	image_list=[], 
	mark_list=[], 
	mark_symbols=[], 
	stop_points=[]):
	if len(fact_track_line)>0:
		lat = np.mean([p[0] for p in fact_track_line])
		lon = np.mean([p[1] for p in fact_track_line])
		# lat = fact_track['coords']['lat'].mean()
		# lon = fact_track['coords']['lon'].mean()
	elif len(plan_track_line)>0:
		lat = np.mean([p[0] for p in plan_track_line])
		lon = np.mean([p[1] for p in plan_track_line])
		# lat = plan_track['coords']['lat'].mean()
		# lon = plan_track['coords']['lon'].mean()
	elif len(poi_list)>0:
		lat=np.mean([m.location[0] for m in poi_list])
		lon=np.mean([m.location[1] for m in poi_list])
	else:
		lat=0
		lon=0
	map_view = folium.Map(location=[lat, lon], zoom_start=12,
			 control_scale=True, scrollWheelZoom=True)
	if len(mark_list)>0:
		marks_group = folium.FeatureGroup(name = 'Разметка').add_to(map_view)
		for m in mark_list:	
			m.add_to(marks_group)
		for ms in mark_symbols:
			ms.add_to(marks_group)
	if len(plan_track_line)>0:
		t1 = folium.FeatureGroup(name = 'Плановый трек')
		map_view.add_child(t1)
		folium.PolyLine(plan_track_line, color="blue", weight=5, opacity=0.5).add_to(t1)
	if len(fact_track_line)>0:
		t2 = folium.FeatureGroup(name = 'Фактический трек')
		map_view.add_child(t2)
		folium.PolyLine(fact_track_line, color="magenta", weight=5, opacity=0.5).add_to(t2)
	if not color_line==None and not colormap==None:
		t3 = folium.FeatureGroup(name = 'Обработанный трек')
		map_view.add_child(t3)
		color_line.add_to(t3)
		map_view.add_child(colormap)
	elif len(proc_track_line)>0:
		t3 = folium.FeatureGroup(name = 'Обработанный трек')
		map_view.add_child(t3)
		folium.PolyLine(proc_track_line, color="red", weight=5, opacity=0.5).add_to(t3)
	if len(stop_points)>0:
		stops_cluster = MarkerCluster(name = 'Остановки', disableClusteringAtZoom=15).add_to(map_view)
		for stop in stop_points:
			stop.add_to(stops_cluster)
	if len(poi_list)>0:
		poi_cluster = MarkerCluster(name = 'Заметки', disableClusteringAtZoom=15).add_to(map_view)
		for poi in poi_list:
			poi.add_to(poi_cluster)
	if len(image_list)>0:
		image_cluster = MarkerCluster(name = 'Картинки', disableClusteringAtZoom=15).add_to(map_view)
		for marker in image_list:
			marker.add_to(image_cluster)
	if not stats_mark==None:
		stats_mark.add_to(map_view)
		
	add_layers(map_view)
	llp = folium.LatLngPopup()
	map_view.add_child(llp)
	map_html = get_map_src(map_view._repr_html_())
	return map_html

def clear_results():
	results = Result.query.filter(Result.user_id==session['user_id'])
	for result in results:
		db.session.delete(result)
	db.session.commit()
	return 0
	
def cut_name(name: str) -> str:
	result = name
	list_glas_ru = ['а', 'у', 'о', 'ы', 'и', 'э', 'я', 'ю', 'ё', 'е',
			  'А', 'У', 'О', 'Ы', 'И', 'Э', 'Я', 'Ю', 'Ё', 'Е']
	list_glas_en = ['A', 'E', 'I', 'O', 'U', 'a', 'e', 'i', 'o', 'u']
	for letter in list_glas_ru:
		result = result.replace(letter, '')
	for letter in list_glas_en:
		result = result.replace(letter, '')
	return result	

def locate_from_exif(raw_ExifData):
	lat=None
	lon=None
	shoot_time=None
	if not raw_ExifData is None:
		exifData = {}
		for tag, value in raw_ExifData.items():
			decodedTag = ExifTags.TAGS.get(tag, tag)
			exifData[decodedTag] = value
		if exifData.get('GPSInfo'):
			gpsData = {}
			for tag, value in exifData['GPSInfo'].items():
				decodedTag = ExifTags.GPSTAGS.get(tag, tag)
				gpsData[decodedTag] = value
			try:
				lat = float(gpsData['GPSLatitude'][0][0])/gpsData['GPSLatitude'][0][1]+float(gpsData['GPSLatitude'][1][0])/gpsData['GPSLatitude'][1][1]/60                 +float(gpsData['GPSLatitude'][2][0])/gpsData['GPSLatitude'][2][1]/3600
				if(gpsData['GPSLatitudeRef'] != u'N'):
					lat = -lat
				lon = float(gpsData['GPSLongitude'][0][0])/gpsData['GPSLongitude'][0][1]+float(gpsData['GPSLongitude'][1][0])/gpsData['GPSLongitude'][1][1]/60                 +float(gpsData['GPSLongitude'][2][0])/gpsData['GPSLongitude'][2][1]/3600
				if(gpsData['GPSLongitudeRef'] != u'E'):
					lon = -lon
			except KeyError:
				pass
		else:
			logging.info(exifData['DateTime'])
			shoot_time = datetime.strptime(exifData['DateTime'], '%Y:%m:%d %H:%M:%S').replace(tzinfo=timezone.utc)
			logging.info(shoot_time.tzinfo)
	return lat, lon, shoot_time
