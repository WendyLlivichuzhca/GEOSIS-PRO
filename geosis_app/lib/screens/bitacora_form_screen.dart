import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:location/location.dart';
import 'dart:io';
import 'dart:convert';
import 'dart:ui' as ui;
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import '../services/odoo_service.dart';

class BitacoraFormScreen extends StatefulWidget {
  @override
  _BitacoraFormScreenState createState() => _BitacoraFormScreenState();
}

class _BitacoraFormScreenState extends State<BitacoraFormScreen> {
  final odoo = OdooService();
  String selectedWeather = 'sunny';
  
  final _resumenController = TextEditingController();
  final _personalController = TextEditingController();
  final _equiposController = TextEditingController();
  final _consultasController = TextEditingController();
  
  final GlobalKey _signatureKey = GlobalKey();
  final GlobalKey<SignaturePadState> _sigPadStateKey = GlobalKey<SignaturePadState>();
  
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
        final rawTasks = args['tasks'] as List<dynamic>? ?? [];
        tasks = rawTasks.map((t) => {
          'id': t['id'],
          'name': t['name'],
          'progress': (t['progress'] as num).toInt(),
          'done': (t['progress'] as num) >= 100,
          'notes': '',
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
      imageQuality: 70,
    );
    if (photo != null) {
      setState(() {
        _fotos.add(File(photo.path));
      });
    }
  }

  // 3. CAPTURAR LIENZO DE FIRMA A BASE64
  Future<String?> _getSignatureBase64() async {
    try {
      RenderRepaintBoundary? boundary = _signatureKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) return null;
      ui.Image image = await boundary.toImage(pixelRatio: 3.0);
      ByteData? byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData != null) {
        return base64Encode(byteData.buffer.asUint8List());
      }
    } catch (e) {
      print("DEBUG: Error capturando lienzo de firma: $e");
    }
    return null;
  }

  // 4. ENVIAR REPORTE A ODOO
  Future<void> _submitReport() async {
    if (_resumenController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Por favor, escribe el resumen de actividades.")));
      return;
    }

    setState(() => _isSaving = true);

    // Capturar firma táctil
    String? signatureB64 = await _getSignatureBase64();

    // Convertir fotos a Base64
    List<Map<String, dynamic>> photosData = [];
    for (var f in _fotos) {
      final bytes = await f.readAsBytes();
      photosData.add({
        'base64_image': base64Encode(bytes),
        'caption': 'Evidencia de obra',
      });
    }

    Map<String, dynamic> reportData = {
      'project_id': projectId,
      'date': DateTime.now().toIso8601String().substring(0, 10),
      'weather': selectedWeather,
      'content': _resumenController.text,
      'personal_notes': _personalController.text,
      'equipment_notes': _equiposController.text,
      'contractor_queries': _consultasController.text,
      'latitude': _locationData?.latitude ?? 0.0,
      'longitude': _locationData?.longitude ?? 0.0,
      'tasks': tasks.map((t) => {
        'task_id': t['id'],
        'progress': t['progress'],
        'done': t['done'],
        'notes': t['notes'] ?? '',
      }).toList(),
      'photos': photosData,
      'signature_contractor': signatureB64,
    };

    bool success = await odoo.submitReport(reportData);
    
    setState(() => _isSaving = false);

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("✅ Libro de Obra sincronizado correctamente en Odoo")));
      Navigator.pop(context);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("❌ Error de sincronización con Odoo")));
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
                // CLIMA
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
                // RESUMEN
                Text("Resumen de actividades", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 10),
                _buildTextArea(_resumenController, "Escribe o dicta lo ocurrido hoy..."),

                SizedBox(height: 35),
                // PERSONAL Y EQUIPOS (MIDUVI)
                Text("Recursos en Obra (Personal)", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 10),
                _buildTextArea(_personalController, "Ej: 1 Residente de Obra, 4 Albañiles, 2 Peones...", maxLines: 2),

                SizedBox(height: 25),
                Text("Equipos y Maquinaria Activa", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 10),
                _buildTextArea(_equiposController, "Ej: 1 Retroexcavadora CAT 320, 2 Volquetas...", maxLines: 2),

                SizedBox(height: 35),
                // CONSULTAS AL FISCALIZADOR (MIDUVI)
                Text("Consultas al Fiscalizador", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                SizedBox(height: 10),
                _buildTextArea(_consultasController, "Escribe aquí cualquier consulta técnica o requerimiento de aprobación..."),

                SizedBox(height: 35),
                // TAREAS / RUBROS
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("Avance de Rubros", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                    TextButton(onPressed: () {}, child: Text("+ Agregar Rubro", style: TextStyle(color: Colors.cyanAccent))),
                  ],
                ),
                ...tasks.map((task) => _buildTaskItem(task)).toList(),

                SizedBox(height: 35),
                // FOTOS DE EVIDENCIA
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

                SizedBox(height: 35),
                // PANEL DE FIRMA (MIDUVI)
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text("Firma del Residente (Contratista)", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16)),
                    TextButton(
                      onPressed: () => _sigPadStateKey.currentState?.clear(),
                      child: Text("Limpiar Firma", style: TextStyle(color: Colors.redAccent, fontSize: 12)),
                    ),
                  ],
                ),
                SizedBox(height: 10),
                Container(
                  height: 180,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.02),
                    borderRadius: BorderRadius.circular(15),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(15),
                    child: SignaturePad(
                      key: _sigPadStateKey,
                      boundaryKey: _signatureKey,
                    ),
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
                      : Text("SINCRONIZAR LIBRO DE OBRA", style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.white)),
                  ),
                ),
                SizedBox(height: 40),
              ],
            ),
          ),
          if (_isSaving)
            Container(
              color: Colors.black87,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.cyanAccent),
                    SizedBox(height: 20),
                    Text("Procesando datos y firmas...", style: TextStyle(color: Colors.white, fontSize: 16)),
                    SizedBox(height: 5),
                    Text("Sincronizando con Odoo ERP...", style: TextStyle(color: Colors.white38, fontSize: 12)),
                  ],
                ),
              ),
            )
        ],
      ),
    );
  }

  Widget _buildTextArea(TextEditingController controller, String hint, {int maxLines = 4}) {
    return TextField(
      controller: controller,
      maxLines: maxLines,
      style: TextStyle(color: Colors.white, fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: Colors.white24, fontSize: 13),
        fillColor: Colors.white.withOpacity(0.04),
        filled: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(15), borderSide: BorderSide.none),
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
        crossAxisAlignment: CrossAxisAlignment.start,
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
          SizedBox(height: 5),
          TextField(
            style: TextStyle(color: Colors.white, fontSize: 12),
            decoration: InputDecoration(
              hintText: "Observación o nota del avance...",
              hintStyle: TextStyle(color: Colors.white24, fontSize: 11),
              fillColor: Colors.white.withOpacity(0.02),
              filled: true,
              contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
            ),
            onChanged: (val) => task['notes'] = val,
          )
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

// LIENZO DE FIRMA TÁCTIL PERSONALIZADO
class SignaturePad extends StatefulWidget {
  final GlobalKey boundaryKey;
  SignaturePad({required Key key, required this.boundaryKey}) : super(key: key);
  @override
  SignaturePadState createState() => SignaturePadState();
}

class SignaturePadState extends State<SignaturePad> {
  List<Offset?> points = [];

  void clear() {
    setState(() => points.clear());
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      key: widget.boundaryKey,
      child: Container(
        color: Colors.white.withOpacity(0.03),
        child: GestureDetector(
          onPanUpdate: (details) {
            setState(() {
              RenderBox renderBox = context.findRenderObject() as RenderBox;
              points.add(renderBox.globalToLocal(details.globalPosition));
            });
          },
          onPanEnd: (details) {
            points.add(null);
          },
          child: CustomPaint(
            painter: SignaturePainter(points: points),
            size: Size.infinite,
          ),
        ),
      ),
    );
  }
}

class SignaturePainter extends CustomPainter {
  final List<Offset?> points;
  SignaturePainter({required this.points});

  @override
  void paint(Canvas canvas, Size size) {
    Paint paint = Paint()
      ..color = Colors.cyanAccent
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 3.0;

    for (int i = 0; i < points.length - 1; i++) {
      if (points[i] != null && points[i + 1] != null) {
        canvas.drawLine(points[i]!, points[i + 1]!, paint);
      }
    }
  }

  @override
  bool shouldRepaint(SignaturePainter oldDelegate) => true;
}
