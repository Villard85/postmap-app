#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  postmap/views/views.py
#
from flask import request, redirect, url_for, render_template, send_file
from flask import flash, session, abort, Response, render_template_string
import sqlalchemy
#from werkzeug.utils import secure_filename
from postmap import app
from datetime import datetime, timedelta

import logging

import os

from postmap import db
from postmap.models.tables import Image, Track, Result

from postmap.views.utility import *
#================
# Logging setup
#================

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, 
	level=logging.INFO, 
	datefmt="%H:%M:%S")
	
# comment next line if debug is not needed	
logging.getLogger().setLevel(logging.DEBUG)

#========================
# View functions
#========================

@app.route('/')
def index():
	if session.get('user_id')==None:
		session['user_id'] = random_string(16)
		check_database(3600*4) #drop old enough entries from database table
	return render_template('index.html', results=session.get('results'))
	
@app.route('/about', methods=['GET', 'POST'])
def about():
	return render_template('about.html')
	
@app.route('/add_plan', methods=['POST'])
def add_plan():
	session['results']=False
	clear_results()
	plan_file = request.files['plan-file']
	gpx, info = upload_trk_file(plan_file)
	if gpx == None:
		return redirect(url_for('index'))
	name = plan_file.filename
	segment = gpxpy.gpx.GPXTrackSegment()
	try:
		for seg in gpx.tracks[0].segments:
			 segment.join(seg)
		joint_gpx = gpxpy.gpx.GPX()
		joint_gpx.tracks.append(gpxpy.gpx.GPXTrack())
		joint_gpx.tracks[0].segments.append(segment)
		xml = joint_gpx.to_xml('1.0')
		track_entry = Track(
			user_id = session.get('user_id'),
			name = name,
			trk = xml,
			info = info,
			role = 'План'
		)
		plan_entry = Track.query.filter(Track.user_id==session['user_id'],
				Track.role=='План').first()
		if plan_entry:
			db.session.delete(plan_entry)
			db.session.add(track_entry)
		else:
			db.session.add(track_entry)
		db.session.commit()
		flash('Файл успешно загружен', 'good')
	except sqlalchemy.exc.IntegrityError:
		logging.exception('Exception while adding plan track to database!')
		#flash('Плановый трек уже загружен', 'bad')
	except Exception:
		logging.exception('Exception while adding plan track!')
		flash('Что-то пошло не так', 'bad')
	return redirect(url_for('index'))
	
@app.route('/add_faсt', methods=['POST'])
def add_fact():
	session['results']=False
	clear_results()
	faсt_file = request.files['fact-file']
	gpx, info = upload_trk_file(faсt_file)
	if gpx == None:
		return redirect(url_for('index'))
	name = faсt_file.filename
	segment = gpxpy.gpx.GPXTrackSegment()
	try:
		for seg in gpx.tracks[0].segments:
			 segment.join(seg)
		joint_gpx = gpxpy.gpx.GPX()
		joint_gpx.tracks.append(gpxpy.gpx.GPXTrack())
		joint_gpx.tracks[0].segments.append(segment)
		if joint_gpx.has_times():
			logging.debug(f'add_fakt: GPX has times')
			#joint_gpx.tracks[0].segments[0].points = sorted(joint_gpx.tracks[0].segments[0].points, 
			#	key=lambda point: point.time)
			joint_gpx.tracks[0].segments[0].points[0].speed=0
			joint_gpx.tracks[0].segments[0].points[-1].speed=0
			try:
				joint_gpx.add_missing_speeds()
				speeds = [p.speed for p in joint_gpx.tracks[0].segments[0].points]
				logging.debug(f'add_fakt: point speed example {speeds}')
				logging.debug(f'add_fakt: Speeds added to GPX')
			except NameError:
				logging.debug(f'add_fact: Adding speeds failed')
				pass
		xml = joint_gpx.to_xml('1.0')
		track_entry = Track(
			user_id = session.get('user_id'),
			name = name,
			trk = xml,
			info = info,
			role = 'Факт'
		)
		fact_entry = Track.query.filter(Track.user_id==session['user_id'],
				Track.role=='Факт').first()
		if fact_entry:
			db.session.delete(fact_entry)
			db.session.add(track_entry)
		else:
			db.session.add(track_entry)
		db.session.commit()
		flash('Файл успешно загружен', 'good')
	except sqlalchemy.exc.IntegrityError:
		logging.exception('Exception while adding fact track to database!')
		#flash('Фактический трек уже загружен', 'bad')
	except Exception:
		logging.exception('Exception while adding fact track!')
		flash('Что-то пошло не так', 'bad')
	return redirect(url_for('index'))

@app.route('/add_poi', methods = ['POST'])
def add_poi():
	poi_file = request.files['poi-file']
	gpx, info = upload_trk_file(poi_file)
	if gpx == None:
		return redirect(url_for('index'))
	if len(gpx.waypoints)==0:
		flash('В файле нет путевых точек (POI)', 'bad')
	else:
		xml = gpx.to_xml('1.0')
		name = poi_file.filename
		track_entry = Track(
			user_id = session.get('user_id'),
			name = name,
			trk = xml,
			info = info,
			role = 'Точки'
		)
		try:
			poi_entry = Track.query.filter(Track.user_id==session['user_id'],
				Track.role=='Точки').first()
			if poi_entry:
				db.session.delete(poi_entry)
				db.session.add(track_entry)
			else:
				db.session.add(track_entry)
			db.session.commit()
			flash('Файл успешно загружен', 'good')
		except sqlalchemy.exc.IntegrityError:
			logging.exception('Exception while adding POI file to database!')
			#flash('Файл с точками уже загружен', 'bad')
		except Exception:
			logging.exception('Exception while adding POI!')
			flash('Что-то пошло не так', 'bad')
	return redirect(url_for('index'))	

@app.route('/add_images', methods = ['POST'])
def add_img():
	session['results']=False
	clear_results()
	img_file = request.files['file']
	fname = img_file.filename
	if fname != '':
		file_ext = fname.rsplit('.', 1)[1].lower()
		#print(file_ext)
		if file_ext not in app.config['IMG_EXTENSIONS']:
			flash('Неверное расширение файла', 'bad')
			return 'Недопустимое расширение файла', 400
	#if not re.search('^img[0-9]{8}-[0-9]{6}\.jpg', fname.lower()):
	#	flash('Неверный формат имени файла', 'bad')
	#	return 'Недопустимое имя файла', 400
		try:
			img = pImage.open(img_file)
			exifDataRaw = img._getexif()
			lat, lon, shoot_time = locate_from_exif(exifDataRaw)
			w,h = img.size
			#print("w{0}, h{1}".format(w,h))
			l = min(w,h)
			scale_factor = l//400
			img = img.reduce(scale_factor)
			w,h = img.size
			buf = BytesIO()
			img.save(buf, 'jpeg')
			img_text = base64.b64encode(buf.getbuffer()).decode()
			new_img = Image(
				user_id = session['user_id'],
				name = img_file.filename,
				img = img_text,
				width = w,
				height = h,
				lat=lat,
				lon=lon,
				shoot_time=shoot_time)
			db.session.add(new_img)
			db.session.commit()
			flash('Изображение успешно загружено', 'good')
		except UnidentifiedImageError:
			logging.exception('Error reading image file')
			flash('Изображение не загружено', 'bad')
	return redirect(url_for('index'))

@app.route('/api/trk_data')
def trk_data():
	selection = Track.query.filter(Track.user_id==session['user_id'])
	return {'data': [track.to_dict() for track in selection]}

@app.route('/api/delete_trk', methods=['POST'])
def delete_trk():
	session['results']=False
	data = request.get_json()
	if 'id' not in data:
		abort(400)
	track = Track.query.get(data['id'])
	db.session.delete(track)
	db.session.commit()
	flash('Трек удален', 'good')
	#remove data from database
	return '', 204
	
@app.route('/api/img_data')
def img_data():
	selection = Image.query.filter(Image.user_id==session['user_id'])
	return {'data': [img.to_dict() for img in selection]}

@app.route('/api/delete_img', methods=['POST'])
def delete_img():
	session['results']=False
	data = request.get_json()
	if 'id' not in data:
		abort(400)
	img = Image.query.get(data['id'])
	db.session.delete(img)
	db.session.commit()
	flash('Изображение удалено', 'good')
	#remove data from database
	return '', 204

@app.route('/clear_tracks', methods=['POST'])
def clear_tracks():
	session['results']=False
	db.session.query(Track).filter(Track.user_id==session['user_id']).delete()
	db.session.commit()
	flash('Треки удалены', 'good')
	return redirect(url_for('index'))

@app.route('/clear_images', methods=['POST'])
def clear_images():
	session['results']=False
	db.session.query(Image).filter(Image.user_id==session['user_id']).delete()
	db.session.commit()
	flash('Изображения удалены', 'good')
	return redirect(url_for('index'))

@app.route('/process', methods = ['POST'])
def process():
	ops = request.form
	proc_line = []
	plan_line = []
	fact_line = []
	color_line = None
	colormap = None
	stats_mark = None
	marks = []
	mark_symbols = []
	stop_points = []
	stops_table = {}
	poi = []
	image_markers = []
	name = ''
	fact_entry = Track.query.filter(Track.user_id==session['user_id'], Track.role=='Факт').all()
	if len(fact_entry)==0:
		logging.info('No fact track found')
	else:
		logging.info('Fact track found')
		name = cut_name(fact_entry[0].name[:-4])
		proc_xml = fact_entry[0].trk
		proc_gpx = gpxpy.parse(proc_xml)
		fact_line = make_line(proc_gpx)
		
		if 'Add-images' in ops.keys():
			proc_gpx, image_markers = make_image_points(proc_gpx, int(ops['time-shift']))
			flash('Изображения добавлены', 'good')
		if 'Simplify' in ops.keys():
			#logging.debug(f'proc_gpx: {len(proc_gpx.tracks[0].segments[0].points)}')
			proc_gpx.simplify(float(ops['epsilon']))
			#logging.debug(proc_gpx)
			flash(f'Трек упрощен до {len(proc_gpx.tracks[0].segments[0].points)} точек', 'good')
		if 'Mark' in ops.keys():
			proc_gpx, marks, mark_symbols = make_marks(proc_gpx, float(ops['step'])*1000)
			flash('Разметка выполнена с шагом {:.1f} км'.format(float(ops['step'])), 'good')
		if 'Smooth' in ops.keys():
			proc_gpx.smooth(horizontal=True)
			flash('Трек успешно сглажен', 'good')
		if 'Calculate-stats' in ops.keys():
			proc_gpx, stops_table, stop_points = find_stops(proc_gpx, float(ops['stop-threshold'])/3.6)
		stats_mark = make_stats_mark(proc_gpx, 
					fact_entry[0].name, 
					float(ops['stop-threshold']))
		proc_line = make_line(proc_gpx)
		color_line, colormap = make_speed_colorline(proc_gpx)
		logging.debug(f'Colorline: {color_line}')
		logging.debug(f'Num of waypoints in proc track: {len(proc_gpx.waypoints)}')
	plan_entry = Track.query.filter(Track.user_id==session['user_id'], Track.role=='План').all()
	if len(plan_entry)==0:
		logging.info('No plan track found')
	else:
		logging.info('Plan track found')
		plan_xml = plan_entry[0].trk
		plan_gpx = gpxpy.parse(plan_xml)
		plan_line = make_line(plan_gpx)
	poi_entry = Track.query.filter(Track.user_id==session['user_id'], Track.role=='Точки').all()
	if len(poi_entry)==0:
		logging.info('POI file not found')
	else:
		logging.info('POI file found')
		poi_xml = poi_entry[0].trk
		poi_gpx = gpxpy.parse(poi_xml)
		if len(fact_line)>0:
			proc_gpx, poi = make_poi(proc_gpx, poi_gpx)
		else:
			blank_gpx = gpxpy.gpx.GPX()
			proc_gpx, poi = make_poi(blank_gpx, poi_gpx)
			name = cut_name(poi_entry[0].name[:-4])
	if not name == '' and len(proc_gpx.tracks)>0:
		proc_gpx.tracks[0].name = name
	map_frame = draw_map(plan_line, fact_line, 
						proc_line, color_line,
						colormap, stats_mark, 
						poi, image_markers, marks, 
						mark_symbols, stop_points)
	flash('Карта создана', 'good')
	results_entry = Result.query.filter(Result.user_id==session['user_id'], 
			Result.role_id=='MAP').first()
	if results_entry:
		results_entry.content = map_frame
	else:
		map_page = Result(
				session['user_id'],
				'MAP', map_frame)
		db.session.add(map_page)
	results_entry = Result.query.filter(Result.user_id==session['user_id'], 
			Result.role_id=='GPX').first()
	if len(proc_line)>0 or len(poi)>0:
		if results_entry:
			results_entry.content = proc_gpx.to_xml('1.0')
		else:
			gpx_file = Result(session['user_id'],
						'GPX', proc_gpx.to_xml('1.0'))
			db.session.add(gpx_file)
	db.session.commit()
	session['results']=True
	return redirect(url_for('index'))

@app.route('/show_map', methods=['GET'])
def show_map():
	try:
		results_entry = Result.query.filter(Result.user_id==session['user_id'], 
			Result.role_id=='MAP').first()
		map_frame = results_entry.content
		return render_template('map.html', map_frame=map_frame)
	except KeyError:
		abort(400)

@app.route('/download_gpx')
def download_gpx():
	upload = Result.query.filter(Result.user_id==session['user_id'], 
		Result.role_id=='GPX').first()
	if upload:
		return send_file(BytesIO(upload.content.encode('utf-8')), 
				download_name='result.gpx', as_attachment=True )
	else:
		flash('Отсутствуют файлы для скачивания', 'bad')
		return redirect(url_for('index'))

@app.errorhandler(413)
def large_file(e):
	return 'Слишком большой файл', 413

@app.route('/download/trk_csv')
def download_trk_csv():
	upload = Result.query.filter(Result.user_id==session['user_id'], 
		Result.role_id=='GPX').first()
	if upload:
		gpx = gpxpy.parse(upload.content)
		return send_file(track_to_csv(gpx), 
			download_name='track.csv', as_attachment=True)
	else:
		flash('Отсутствуют файлы для скачивания', 'bad')
		return redirect(url_for('index'))
	
@app.route('/download/pts_csv')
def download_pts_csv():
	upload = Result.query.filter(Result.user_id==session['user_id'], 
		Result.role_id=='GPX').first()
	if upload:
		gpx = gpxpy.parse(upload.content)
		return send_file(wpts_to_csv(gpx), 
			download_name='points.csv', as_attachment=True)
	else:
		flash('Отсутствуют файлы для скачивания', 'bad')
		return redirect(url_for('index'))
