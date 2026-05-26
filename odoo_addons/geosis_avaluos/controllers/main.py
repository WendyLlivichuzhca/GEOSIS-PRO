# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import base64
import logging

_logger = logging.getLogger(__name__)

class GeosisAvaluoMobileAPI(http.Controller):

    def _partner_domain(self):
        commercial_partner = request.env.user.partner_id.commercial_partner_id
        return [('partner_id', 'child_of', commercial_partner.id)]

    @http.route('/web/geosis/avaluos', type='json', auth='user', methods=['POST'])
    def get_avaluos(self):
        """
        Retorna la lista de avalúos asociados al usuario perito (inspector) 
        o al cliente (solicitante).
        """
        try:
            domain = ['|', ('inspector_id', '=', request.env.user.id)] + self._partner_domain()
            avaluos = request.env['geosis.avaluo'].sudo().search(domain, order='date desc, id desc')
            
            data = []
            for av in avaluos:
                # Fotos serializadas (solo metadata para la lista)
                photos = [{
                    'id': photo.id,
                    'name': photo.name or '',
                    'latitude': photo.latitude or 0.0,
                    'longitude': photo.longitude or 0.0,
                } for photo in av.photo_ids]

                # Comparables
                comparables = [{
                    'name': comp.name,
                    'area': comp.area,
                    'price': comp.price,
                    'price_m2': comp.price_m2,
                    'distance_km': comp.distance_km,
                } for comp in av.comparable_ids]

                data.append({
                    'id': av.id,
                    'code': av.name,
                    'title': av.title or '',
                    'owner_name': av.owner_name or '',
                    'partner_name': av.partner_id.name or '',
                    'inspector_name': av.inspector_id.name or '',
                    'date': str(av.date) if av.date else '',
                    'state': av.state,
                    'location': av.location or '',
                    'latitude': av.latitude or 0.0,
                    'longitude': av.longitude or 0.0,
                    
                    # Terreno
                    'land_area': av.land_area or 0.0,
                    'land_unit_value': av.land_unit_value or 0.0,
                    'land_topography_factor': av.land_topography_factor or 1.0,
                    'land_shape_factor': av.land_shape_factor or 1.0,
                    'land_value': av.land_value or 0.0,

                    # Construcción
                    'construction_area': av.construction_area or 0.0,
                    'construction_replacement_cost': av.construction_replacement_cost or 0.0,
                    'construction_age': av.construction_age or 0,
                    'construction_life_expectancy': av.construction_life_expectancy or 50,
                    'construction_state_coef': av.construction_state_coef or '1.00',
                    'construction_depreciation_percent': av.construction_depreciation_percent or 0.0,
                    'construction_value': av.construction_value or 0.0,

                    # Totales
                    'total_value': av.total_value or 0.0,
                    'photos': photos,
                    'comparables': comparables,
                })
            
            return {'status': 'success', 'data': data}
        except Exception as exc:
            _logger.error("Error al obtener avalúos: %s", exc)
            return {'status': 'error', 'message': str(exc)}

    @http.route('/web/geosis/submit_avaluo', type='json', auth='user', methods=['POST'])
    def submit_avaluo(self):
        """
        Recibe la inspección física de campo de un avalúo, guarda fotos/comparables
        y ejecuta las depreciaciones físicas mediante Ross-Heidecke.
        """
        try:
            params = request.get_json_data().get('params', {})
            data = params.get('avaluo')
            if not data:
                return {'status': 'error', 'message': 'No se proporcionaron datos del avalúo'}

            av_id = data.get('id')
            if not av_id:
                return {'status': 'error', 'message': 'ID de avalúo faltante'}

            # Buscar avalúo (sudo para perito/cliente)
            avaluo = request.env['geosis.avaluo'].sudo().browse(int(av_id))
            if not avaluo.exists():
                return {'status': 'error', 'message': 'El avalúo especificado no existe'}

            # Valores generales e inspección
            vals = {
                'location': data.get('location') or avaluo.location,
                'latitude': float(data.get('latitude', 0.0) or avaluo.latitude),
                'longitude': float(data.get('longitude', 0.0) or avaluo.longitude),
                
                # Terreno
                'land_area': float(data.get('land_area', 0.0) or avaluo.land_area),
                'land_unit_value': float(data.get('land_unit_value', 0.0) or avaluo.land_unit_value),
                'land_topography_factor': float(data.get('land_topography_factor', 1.0) or avaluo.land_topography_factor),
                'land_shape_factor': float(data.get('land_shape_factor', 1.0) or avaluo.land_shape_factor),
                
                # Construcción
                'construction_area': float(data.get('construction_area', 0.0) or avaluo.construction_area),
                'construction_replacement_cost': float(data.get('construction_replacement_cost', 0.0) or avaluo.construction_replacement_cost),
                'construction_age': int(data.get('construction_age', 0) or avaluo.construction_age),
                'construction_life_expectancy': int(data.get('construction_life_expectancy', 50) or avaluo.construction_life_expectancy),
                'construction_state_coef': data.get('construction_state_coef') or avaluo.construction_state_coef,
                
                'state': 'inspected'
            }

            # Escribir en el avalúo principal
            avaluo.write(vals)

            # --- PROCESAR FOTOGRAFÍAS ---
            photos_data = data.get('photos') or []
            if photos_data:
                # Limpiar fotos previas
                avaluo.photo_ids.unlink()
                photo_vals = []
                for p in photos_data:
                    img_data = p.get('image')
                    if img_data:
                        # Si viene con prefijo data:image/png;base64, etc, lo removemos
                        if ',' in img_data:
                            img_data = img_data.split(',')[1]
                        
                        photo_vals.append({
                            'avaluo_id': avaluo.id,
                            'name': p.get('name', 'Foto de Inspección'),
                            'image': img_data,
                            'latitude': float(p.get('latitude', 0.0) or 0.0),
                            'longitude': float(p.get('longitude', 0.0) or 0.0),
                        })
                if photo_vals:
                    request.env['geosis.avaluo.photo'].create(photo_vals)

            # --- PROCESAR COMPARABLES ---
            comparables_data = data.get('comparables') or []
            if comparables_data:
                # Limpiar comparables previos
                avaluo.comparable_ids.unlink()
                comp_vals = []
                for c in comparables_data:
                    comp_vals.append({
                        'avaluo_id': avaluo.id,
                        'name': c.get('name', 'Propiedad Comparable'),
                        'area': float(c.get('area', 1.0) or 1.0),
                        'price': float(c.get('price', 0.0) or 0.0),
                        'distance_km': float(c.get('distance_km', 0.0) or 0.0),
                    })
                if comp_vals:
                    request.env['geosis.avaluo.comparable'].create(comp_vals)

            # --- EJECUTAR CÁLCULO CIENTÍFICO Y PASAR A CALCULADO ---
            avaluo.action_calculate()

            return {
                'status': 'success',
                'message': 'Inspección de avalúo subida e integrada correctamente',
                'data': {
                    'id': avaluo.id,
                    'code': avaluo.name,
                    'depreciation_percent': avaluo.construction_depreciation_percent,
                    'land_value': avaluo.land_value,
                    'construction_value': avaluo.construction_value,
                    'total_value': avaluo.total_value,
                }
            }
        except Exception as exc:
            _logger.error("Error al subir inspección de avalúo: %s", exc)
            return {'status': 'error', 'message': str(exc)}
