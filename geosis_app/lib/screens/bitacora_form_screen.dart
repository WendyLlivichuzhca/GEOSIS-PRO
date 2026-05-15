import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:location/location.dart';
import 'dart:io';
import 'dart:convert';
import '../services/odoo_service.dart';

class BitacoraFormScreen extends StatefulWidget {
  @override
  _BitacoraFormScreenState createState() => _BitacoraFormScreenState();
}

class _BitacoraFormScreenState extends State<BitacoraFormScreen> {
  final odoo = OdooService();
  String selectedWeather = 'sunny';
  final _resumenController = TextEditingController();
  
  List<Map<String, dynamic>> tasks = [];
  String projectName = "";
  int? projectId;

  List<File> _fotos = [];
  final ImagePicker _picker = ImagePicker();
  LocationData? _locationData;
  bool _isSaving = false;
  bool _isInitialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_isInitialized) {
      final args = ModalRoute.of(context)?.settings.arguments as Map<String, dynamic>?;
      if (args != null) {
        projectId = args['project_id'];
        projectName = args['project_name'];
        // Convertimos las tareas de la API al formato que usa el formulario
        final rawTasks = args['tasks'] as List<dynamic>? ?? [];
        tasks = rawTasks.map((t) => {
          'id': t['id'],
          'name': t['name'],
          'progress': (t['progress'] as num).toInt(),
          'done': (t['progress'] as num) >= 100,
        }).toList();
      }
      _isInitialized = true;
    }
  }

  @override
  void initState() {
    super.initState();
    _getLocation();
  }

  // 1. OBTENER GPS
  Future<void> _getLocation() async {
    Location location = Location();
    bool _serviceEnabled;
    PermissionStatus _permissionGranted;

    _serviceEnabled = await location.serviceEnabled();
    if (!_serviceEnabled) {
      _serviceEnabled = await location.requestService();
      if (!_serviceEnabled) return;
    }

    _permissionGranted = await location.hasPermission();
    if (_permissionGranted == PermissionStatus.denied) {
      _permissionGranted = await location.requestPermission();
      if (_permissionGranted != PermissionStatus.granted) return;
    }

    _locationData = await location.getLocation();
  }

  // 2. TOMAR FOTO CON LA CÁMARA
  Future<void> _takePhoto() async {
    final XFile? photo = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70, // Comprimimos un poco para Odoo
    );
    if (photo != null) {
      setState(() {
        _fotos.add(File(photo.path));
      });
    }
  }

  // 3. ENVIAR REPORTE A ODOO
  Future<void> _submitReport() async {
    if (_resumenController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Por favor, escribe un resumen de actividades.")));
      return;
    }

    setState(() => _isSaving = true);

    // Convertir fotos a Base64 para Odoo
    List<String> fotosBase64 = [];
    for (var f in _fotos) {
      final bytes = await f.readAsBytes();
      fotosBase64.add(base64Encode(bytes));
    }

    Map<String, dynamic> reportData = {
      'weather': selectedWeather,
      'summary': _resumenController.text,
      'latitude': _locationData?.latitude ?? 0.0,
      'longitude': _locationData?.longitude ?? 0.0,
      'tasks': tasks,
      'photos': fotosBase64,
      'date': DateTime.now().toIso8601String(),
    };

    bool success = await odoo.submitReport(reportData);
    
    setState(() => _isSaving = false);

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("✅ Bitácora guardada en Odoo exitosamente")));
      Navigator.pop(context); // Regresar al dashboard
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("❌ Error al guardar en Odoo")));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFF0D1B2A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text("Nuevo Reporte Diario", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
        leading: IconButton(icon: Icon(Icons.arrow_back_ios, color: Colors.white), onPressed: () => Navigator.pop(context)),
      ),
      body: Stack(
        children: [
          SingleChildScrollView(
            padding: EdgeInsets.all(25),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // SECTOR DE CLIMA
                Text("¿Cómo está el clima hoy?", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 15),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildWeatherIcon(Icons.wb_sunny, 'sunny', 'Soleado'),
                    _buildWeatherIcon(Icons.cloud, 'cloudy', 'Nublado'),
                    _buildWeatherIcon(Icons.umbrella, 'rainy', 'Lluvia'),
                    _buildWeatherIcon(Icons.flash_on, 'storm', 'Tormenta'),
                  ],
                ),

                SizedBox(height: 35),
                // RESUMEN DEL DIA
                Text("Resumen de actividades", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 10),
                TextField(
                  controller: _resumenController,
                  maxLines: 4,
                  style: TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: "Escribe o dicta lo ocurrido hoy...",
                    hintStyle: TextStyle(color: Colors.white24),
                    fillColor: Colors.white.withOpacity(0.05),
                    filled: true,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(15), borderSide: BorderSide.none),
                  ),
                ),

                SizedBox(height: 35),
                // TAREAS / RUBROS
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("Avance de Tareas", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                    TextButton(onPressed: () {}, child: Text("+ Agregar Tarea", style: TextStyle(color: Colors.cyanAccent))),
                  ],
                ),
                ...tasks.map((task) => _buildTaskItem(task)).toList(),

                SizedBox(height: 35),
                // EVIDENCIA FOTOGRAFICA
                Text("Fotos de Evidencia", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 15),
                Container(
                  height: 120,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: [
                      GestureDetector(
                        onTap: _takePhoto,
                        child: Container(
                          width: 100,
                          margin: EdgeInsets.only(right: 15),
                          decoration: BoxDecoration(
                            color: Colors.cyanAccent.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(15),
                            border: Border.all(color: Colors.cyanAccent.withOpacity(0.5)),
                          ),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.camera_alt, color: Colors.cyanAccent, size: 30),
                              SizedBox(height: 5),
                              Text("Tomar Foto", style: TextStyle(color: Colors.cyanAccent, fontSize: 10)),
                            ],
                          ),
                        ),
                      ),
                      ..._fotos.map((f) => _buildPhotoItem(f)).toList(),
                    ],
                  ),
                ),

                SizedBox(height: 50),
                // BOTON GUARDAR
                SizedBox(
                  width: double.infinity,
                  height: 60,
                  child: ElevatedButton(
                    onPressed: _isSaving ? null : _submitReport,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                    ),
                    child: _isSaving 
                      ? CircularProgressIndicator(color: Colors.white)
                      : Text("GUARDAR Y SINCRONIZAR", style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.white)),
                  ),
                ),
                SizedBox(height: 40),
              ],
            ),
          ),
          if (_isSaving)
            Container(
              color: Colors.black54,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.cyanAccent),
                    SizedBox(height: 15),
                    Text("Subiendo a Odoo...", style: TextStyle(color: Colors.white, fontSize: 16)),
                  ],
                ),
              ),
            )
        ],
      ),
    );
  }

  Widget _buildWeatherIcon(IconData icon, String value, String label) {
    bool isSelected = selectedWeather == value;
    return GestureDetector(
      onTap: () => setState(() => selectedWeather = value),
      child: Column(
        children: [
          Container(
            padding: EdgeInsets.all(15),
            decoration: BoxDecoration(
              color: isSelected ? Colors.cyanAccent.withOpacity(0.2) : Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: isSelected ? Colors.cyanAccent : Colors.white10),
            ),
            child: Icon(icon, color: isSelected ? Colors.cyanAccent : Colors.white38),
          ),
          SizedBox(height: 5),
          Text(label, style: TextStyle(color: isSelected ? Colors.cyanAccent : Colors.white38, fontSize: 10)),
        ],
      ),
    );
  }

  Widget _buildTaskItem(Map<String, dynamic> task) {
    return Container(
      margin: EdgeInsets.only(bottom: 15),
      padding: EdgeInsets.all(15),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(15), border: Border.all(color: Colors.white10)),
      child: Column(
        children: [
          Row(
            children: [
              Checkbox(
                value: task['done'],
                onChanged: (val) => setState(() => task['done'] = val),
                activeColor: Colors.cyanAccent,
                checkColor: Colors.black,
                side: BorderSide(color: Colors.white24),
              ),
              Expanded(child: Text(task['name'], style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500))),
              Text("${task['progress']}%", style: TextStyle(color: Colors.cyanAccent, fontSize: 12, fontWeight: FontWeight.bold)),
            ],
          ),
          Slider(
            value: task['progress'].toDouble(),
            min: 0, max: 100,
            activeColor: Colors.cyanAccent,
            inactiveColor: Colors.white10,
            onChanged: (val) => setState(() => task['progress'] = val.toInt()),
          ),
        ],
      ),
    );
  }

  Widget _buildPhotoItem(File file) {
    return Container(
      width: 100,
      margin: EdgeInsets.only(right: 15),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white24),
        image: DecorationImage(image: FileImage(file), fit: BoxFit.cover),
      ),
      child: Align(
        alignment: Alignment.topRight,
        child: GestureDetector(
          onTap: () => setState(() => _fotos.remove(file)),
          child: Container(
            margin: EdgeInsets.all(5),
            decoration: BoxDecoration(color: Colors.redAccent, shape: BoxShape.circle),
            child: Icon(Icons.close, color: Colors.white, size: 16),
          ),
        ),
      ),
    );
  }
}
