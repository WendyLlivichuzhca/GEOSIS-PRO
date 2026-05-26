import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:location/location.dart';
import '../services/odoo_service.dart';

class AvaluoFormScreen extends StatefulWidget {
  final dynamic avaluo;

  AvaluoFormScreen({required this.avaluo});

  @override
  _AvaluoFormScreenState createState() => _AvaluoFormScreenState();
}

class _AvaluoFormScreenState extends State<AvaluoFormScreen> {
  final odoo = OdooService();
  final _picker = ImagePicker();
  LocationData? _locationData;

  // Controladores de texto
  final _locationController = TextEditingController();
  final _latitudeController = TextEditingController();
  final _longitudeController = TextEditingController();

  // Terreno
  final _landAreaController = TextEditingController();
  final _landUnitValueController = TextEditingController();
  final _landTopographyController = TextEditingController();
  final _landShapeController = TextEditingController();

  // Construcción
  final _constAreaController = TextEditingController();
  final _constReplacementCostController = TextEditingController();
  final _constAgeController = TextEditingController();
  final _constLifeExpectancyController = TextEditingController();
  String selectedStateCoef = "1.00"; // Coeficiente Ross-Heidecke

  // Comparables y Fotos
  List<Map<String, dynamic>> comparables = [];
  List<InspectedPhoto> _fotos = [];

  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    // Cargar datos iniciales del avalúo
    final av = widget.avaluo;
    _locationController.text = av['location'] ?? '';
    _latitudeController.text = (av['latitude'] ?? 0.0).toString();
    _longitudeController.text = (av['longitude'] ?? 0.0).toString();

    _landAreaController.text = (av['land_area'] ?? 0.0).toString();
    _landUnitValueController.text = (av['land_unit_value'] ?? 0.0).toString();
    _landTopographyController.text = (av['land_topography_factor'] ?? 1.0).toString();
    _landShapeController.text = (av['land_shape_factor'] ?? 1.0).toString();

    _constAreaController.text = (av['construction_area'] ?? 0.0).toString();
    _constReplacementCostController.text = (av['construction_replacement_cost'] ?? 0.0).toString();
    _constAgeController.text = (av['construction_age'] ?? 0).toString();
    _constLifeExpectancyController.text = (av['construction_life_expectancy'] ?? 50).toString();
    selectedStateCoef = av['construction_state_coef'] ?? '1.00';

    final rawComparables = av['comparables'] as List<dynamic>? ?? [];
    comparables = rawComparables.map((c) => {
      'name': c['name'] ?? '',
      'area': (c['area'] as num?)?.toDouble() ?? 0.0,
      'price': (c['price'] as num?)?.toDouble() ?? 0.0,
      'distance_km': (c['distance_km'] as num?)?.toDouble() ?? 0.0,
    }).toList();

    _getLocation();
  }

  Future<void> _getLocation() async {
    Location location = Location();
    bool _serviceEnabled;
    PermissionStatus _permissionGranted;

    try {
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
      if (_locationData != null) {
        setState(() {
          _latitudeController.text = _locationData!.latitude.toString();
          _longitudeController.text = _locationData!.longitude.toString();
        });
      }
    } catch (e) {
      print("DEBUG: Error al obtener geolocalización: $e");
    }
  }

  Future<void> _takePhoto() async {
    final XFile? photo = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );
    if (photo != null) {
      double lat = 0.0;
      double lng = 0.0;
      if (_locationData != null) {
        lat = _locationData!.latitude ?? 0.0;
        lng = _locationData!.longitude ?? 0.0;
      }
      setState(() {
        _fotos.add(InspectedPhoto(
          file: File(photo.path),
          latitude: lat,
          longitude: lng,
          caption: "Foto de Inspección",
        ));
      });
    }
  }

  void _addComparableDialog() {
    final compName = TextEditingController();
    final compArea = TextEditingController();
    final compPrice = TextEditingController();
    final compDistance = TextEditingController();

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF0D1B2E),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: Colors.white10),
        ),
        title: Text(
          "Agregar Comparable",
          style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
        ),
        content: SingleChildScrollView(
          child: Column(
            children: [
              _buildDialogField(compName, "Nombre / Referencia (e.g. Terreno Urdesa)"),
              SizedBox(height: 10),
              _buildDialogField(compArea, "Área (m²)", isNumeric: true),
              SizedBox(height: 10),
              _buildDialogField(compPrice, "Precio (USD)", isNumeric: true),
              SizedBox(height: 10),
              _buildDialogField(compDistance, "Distancia (km)", isNumeric: true),
            ],
          ),
        ),
        actions: [
          TextButton(
            child: Text("Cancelar", style: TextStyle(color: Colors.white54)),
            onPressed: () => Navigator.pop(context),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text("Agregar", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            onPressed: () {
              if (compName.text.isNotEmpty) {
                setState(() {
                  comparables.add({
                    'name': compName.text,
                    'area': double.tryParse(compArea.text) ?? 0.0,
                    'price': double.tryParse(compPrice.text) ?? 0.0,
                    'distance_km': double.tryParse(compDistance.text) ?? 0.0,
                  });
                });
                Navigator.pop(context);
              }
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDialogField(TextEditingController controller, String hint, {bool isNumeric = false}) {
    return TextField(
      controller: controller,
      keyboardType: isNumeric ? TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      style: TextStyle(color: Colors.white, fontSize: 13),
      decoration: InputDecoration(
        labelText: hint,
        labelStyle: TextStyle(color: Colors.white38),
        fillColor: Colors.white.withOpacity(0.04),
        filled: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
      ),
    );
  }

  Future<void> _submitInspection() async {
    setState(() => _isSaving = true);

    // Formatear fotos
    List<Map<String, dynamic>> photosData = [];
    for (var f in _fotos) {
      final bytes = await f.file.readAsBytes();
      photosData.add({
        'name': f.caption,
        'image': base64Encode(bytes),
        'latitude': f.latitude,
        'longitude': f.longitude,
      });
    }

    Map<String, dynamic> avaluoData = {
      'id': widget.avaluo['id'],
      'location': _locationController.text,
      'latitude': double.tryParse(_latitudeController.text) ?? 0.0,
      'longitude': double.tryParse(_longitudeController.text) ?? 0.0,

      // Terreno
      'land_area': double.tryParse(_landAreaController.text) ?? 0.0,
      'land_unit_value': double.tryParse(_landUnitValueController.text) ?? 0.0,
      'land_topography_factor': double.tryParse(_landTopographyController.text) ?? 1.0,
      'land_shape_factor': double.tryParse(_landShapeController.text) ?? 1.0,

      // Edificación
      'construction_area': double.tryParse(_constAreaController.text) ?? 0.0,
      'construction_replacement_cost': double.tryParse(_constReplacementCostController.text) ?? 0.0,
      'construction_age': int.tryParse(_constAgeController.text) ?? 0,
      'construction_life_expectancy': int.tryParse(_constLifeExpectancyController.text) ?? 50,
      'construction_state_coef': selectedStateCoef,

      'photos': photosData,
      'comparables': comparables,
    };

    Map<String, dynamic>? responseResult;
    try {
      responseResult = await odoo.submitAvaluo(avaluoData);
    } catch (e) {
      print("DEBUG: Falló envío en submitAvaluo: $e");
      responseResult = null;
    }

    setState(() => _isSaving = false);

    if (responseResult != null && responseResult['status'] == 'success') {
      final data = responseResult['data'];
      _showSuccessDialog(data);
    } else {
      // Offline dialog
      _showOfflineDialog(avaluoData);
    }
  }

  void _showSuccessDialog(dynamic data) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF0D1B2E),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(25),
          side: BorderSide(color: Colors.white10),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.check_circle_outline, color: Colors.greenAccent, size: 50),
            SizedBox(height: 10),
            Text(
              "INSPECCIÓN PROCESADA",
              style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1.5),
            ),
            SizedBox(height: 5),
            Text(
              "Cálculo Ross-Heidecke Completo",
              style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
            ),
          ],
        ),
        content: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: double.infinity,
              padding: EdgeInsets.all(15),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [Colors.blueAccent.withOpacity(0.2), Colors.cyanAccent.withOpacity(0.1)]),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
              ),
              child: Column(
                children: [
                  Text("VALORACIÓN COMERCIAL TOTAL", style: TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  Text(
                    "\$${(data['total_value'] ?? 0.0).toStringAsFixed(2)} USD",
                    style: GoogleFonts.outfit(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            SizedBox(height: 15),
            _resultRow("Código Avalúo:", "${data['code']}"),
            _resultRow("Depreciación Fís.:", "${(data['depreciation_percent'] ?? 0.0).toStringAsFixed(2)}%"),
            _resultRow("Valor Terreno:", "\$${(data['land_value'] ?? 0.0).toStringAsFixed(2)} USD"),
            _resultRow("Valor Edific.:", "\$${(data['construction_value'] ?? 0.0).toStringAsFixed(2)} USD"),
          ],
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () {
              Navigator.pop(context); // Cerrar diálogo
              Navigator.pop(context); // Regresar al listado
            },
            child: Text("Finalizar", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  void _showOfflineDialog(Map<String, dynamic> avaluoData) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF0D1B2E),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: Colors.white10),
        ),
        title: Row(
          children: [
            Icon(Icons.signal_wifi_connected_no_internet_4, color: Colors.orangeAccent),
            SizedBox(width: 10),
            Text(
              "Guardado Local (Offline)",
              style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
            ),
          ],
        ),
        content: Text(
          "No pudimos conectar con Odoo. ¿Deseas guardar este avalúo localmente en el móvil para sincronizarlo cuando tengas internet?",
          style: GoogleFonts.outfit(color: Colors.white70, fontSize: 13, height: 1.4),
        ),
        actions: [
          TextButton(
            child: Text("Seguir intentando", style: TextStyle(color: Colors.cyanAccent)),
            onPressed: () => Navigator.pop(context),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.orangeAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: Text("Guardar en Móvil", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            onPressed: () async {
              Navigator.pop(context); // Cerrar diálogo
              setState(() => _isSaving = true);
              await odoo.saveOfflineAvaluo(avaluoData);
              setState(() => _isSaving = false);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  backgroundColor: Colors.orangeAccent,
                  content: Text("✅ Avalúo guardado en cola offline. Sincronízalo desde el Dashboard.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
                ),
              );
              Navigator.pop(context); // Regresar al listado
            },
          ),
        ],
      ),
    );
  }

  Widget _resultRow(String label, String val) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: GoogleFonts.outfit(color: Colors.white54, fontSize: 12)),
          Text(val, style: GoogleFonts.outfit(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        backgroundColor: Color(0xFF0D1B2A),
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: Text(
            "${widget.avaluo['code'] ?? 'Inspección'}",
            style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
          ),
          leading: IconButton(
            icon: Icon(Icons.arrow_back_ios, color: Colors.white),
            onPressed: () => Navigator.pop(context),
          ),
          bottom: TabBar(
            indicatorColor: Colors.cyanAccent,
            labelColor: Colors.cyanAccent,
            unselectedLabelColor: Colors.white38,
            labelStyle: GoogleFonts.outfit(fontSize: 12, fontWeight: FontWeight.bold),
            tabs: [
              Tab(text: "Terreno & Ubic.", icon: Icon(Icons.map, size: 20)),
              Tab(text: "Edificación", icon: Icon(Icons.home_work, size: 20)),
              Tab(text: "Fotos & Mercado", icon: Icon(Icons.camera_alt, size: 20)),
            ],
          ),
        ),
        body: Stack(
          children: [
            TabBarView(
              physics: BouncingScrollPhysics(),
              children: [
                _buildTerrenoTab(),
                _buildEdificacionTab(),
                _buildFotosMercadoTab(),
              ],
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
                      Text("Procesando inspección...", style: TextStyle(color: Colors.white, fontSize: 16)),
                      Text("Enviando y calculando en Odoo...", style: TextStyle(color: Colors.white38, fontSize: 12)),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildTerrenoTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Ubicación Referencial", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
          SizedBox(height: 10),
          _buildInput(_locationController, "Dirección Completa (e.g. Urdesa, Calle 4ta)"),
          SizedBox(height: 15),
          Row(
            children: [
              Expanded(child: _buildInput(_latitudeController, "Latitud", isNumeric: true)),
              SizedBox(width: 15),
              Expanded(child: _buildInput(_longitudeController, "Longitud", isNumeric: true)),
            ],
          ),
          SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.blueAccent.withOpacity(0.15),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: BorderSide(color: Colors.blueAccent.withOpacity(0.4)),
                ),
              ),
              onPressed: _getLocation,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.my_location, color: Colors.cyanAccent, size: 16),
                  SizedBox(width: 8),
                  Text("Actualizar Coordenadas GPS", style: GoogleFonts.outfit(color: Colors.cyanAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ),
          SizedBox(height: 35),
          Text("Ficha del Terreno", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
          SizedBox(height: 10),
          _buildInput(_landAreaController, "Área del Terreno (m²)", isNumeric: true),
          SizedBox(height: 15),
          _buildInput(_landUnitValueController, "Valor Unitario Base (\$/m²)", isNumeric: true),
          SizedBox(height: 15),
          Row(
            children: [
              Expanded(child: _buildInput(_landTopographyController, "Factor Topografía", isNumeric: true)),
              SizedBox(width: 15),
              Expanded(child: _buildInput(_landShapeController, "Factor Forma", isNumeric: true)),
            ],
          ),
          SizedBox(height: 10),
          Text(
            "* Los factores suelen variar entre 0.8 y 1.0, siendo 1.0 el estado óptimo.",
            style: GoogleFonts.outfit(color: Colors.white24, fontSize: 10, fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }

  Widget _buildEdificacionTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Construcción e Infraestructura", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
          SizedBox(height: 10),
          _buildInput(_constAreaController, "Área de Construcción (m²)", isNumeric: true),
          SizedBox(height: 15),
          _buildInput(_constReplacementCostController, "Costo Reposición Nuevo (\$/m²)", isNumeric: true),
          SizedBox(height: 15),
          Row(
            children: [
              Expanded(child: _buildInput(_constAgeController, "Antigüedad (Años)", isNumeric: true)),
              SizedBox(width: 15),
              Expanded(child: _buildInput(_constLifeExpectancyController, "Expectativa Vida Útil (Años)", isNumeric: true)),
            ],
          ),
          SizedBox(height: 25),
          Text("Estado de Conservación (Ross-Heidecke)", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
          SizedBox(height: 12),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 15),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.04),
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: Colors.white10),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: selectedStateCoef,
                dropdownColor: Color(0xFF0D1B2E),
                style: GoogleFonts.outfit(color: Colors.white, fontSize: 14),
                icon: Icon(Icons.arrow_drop_down, color: Colors.cyanAccent),
                onChanged: (val) {
                  if (val != null) setState(() => selectedStateCoef = val);
                },
                items: [
                  DropdownMenuItem(value: "1.00", child: Text("Perfecto / Nuevo (1.00)")),
                  DropdownMenuItem(value: "0.95", child: Text("Bueno / Conservado (0.95)")),
                  DropdownMenuItem(value: "0.75", child: Text("Regular / Reparaciones Simples (0.75)")),
                  DropdownMenuItem(value: "0.40", child: Text("Malo / Reparación Estructural (0.40)")),
                  DropdownMenuItem(value: "0.00", child: Text("Ruina / Obsoleto (0.00)")),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFotosMercadoTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.all(22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("Fotos de Evidencia de Inspección", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
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
                      color: Colors.cyanAccent.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: Colors.cyanAccent.withOpacity(0.3)),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.camera_alt, color: Colors.cyanAccent, size: 28),
                        SizedBox(height: 6),
                        Text("Tomar Foto", style: GoogleFonts.outfit(color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),
                ),
                ..._fotos.map((ph) => _buildPhotoItem(ph)).toList(),
              ],
            ),
          ),
          SizedBox(height: 35),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text("Muestras Comparables de Mercado", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14, fontWeight: FontWeight.bold)),
              IconButton(
                icon: Icon(Icons.add_circle, color: Colors.cyanAccent),
                onPressed: _addComparableDialog,
              )
            ],
          ),
          SizedBox(height: 10),
          comparables.isEmpty
              ? Container(
                  width: double.infinity,
                  padding: EdgeInsets.all(20),
                  decoration: BoxDecoration(color: Colors.white.withOpacity(0.02), borderRadius: BorderRadius.circular(15)),
                  child: Center(
                    child: Text("No se han agregado comparables del sector", style: GoogleFonts.outfit(color: Colors.white24, fontSize: 12)),
                  ),
                )
              : Column(
                  children: comparables.map((c) => _buildComparableItem(c)).toList(),
                ),
          SizedBox(height: 45),
          SizedBox(
            width: double.infinity,
            height: 55,
            child: ElevatedButton(
              onPressed: _submitInspection,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.cyanAccent,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
              ),
              child: Text("SINCRONIZAR AVALÚO", style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.black)),
            ),
          ),
          SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _buildPhotoItem(InspectedPhoto ph) {
    return Container(
      width: 100,
      margin: EdgeInsets.only(right: 15),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white24),
        image: DecorationImage(image: FileImage(ph.file), fit: BoxFit.cover),
      ),
      child: Stack(
        children: [
          Align(
            alignment: Alignment.topRight,
            child: GestureDetector(
              onTap: () => setState(() => _fotos.remove(ph)),
              child: Container(
                margin: EdgeInsets.all(5),
                decoration: BoxDecoration(color: Colors.redAccent, shape: BoxShape.circle),
                child: Icon(Icons.close, color: Colors.white, size: 16),
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              padding: EdgeInsets.symmetric(vertical: 2, horizontal: 4),
              color: Colors.black54,
              child: Text(
                "GPS OK",
                style: TextStyle(color: Colors.greenAccent, fontSize: 8, fontWeight: FontWeight.bold),
              ),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildComparableItem(Map<String, dynamic> c) {
    return Container(
      margin: EdgeInsets.only(bottom: 10),
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(c['name'], style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                SizedBox(height: 3),
                Text(
                  "Área: ${c['area']} m² | Precio: \$${c['price']} | Distancia: ${c['distance_km']} km",
                  style: GoogleFonts.outfit(color: Colors.white38, fontSize: 11),
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(Icons.delete_outline, color: Colors.redAccent, size: 18),
            onPressed: () {
              setState(() {
                comparables.remove(c);
              });
            },
          )
        ],
      ),
    );
  }

  Widget _buildInput(TextEditingController controller, String label, {bool isNumeric = false}) {
    return TextField(
      controller: controller,
      keyboardType: isNumeric ? TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      style: TextStyle(color: Colors.white, fontSize: 13),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: Colors.white38, fontSize: 12),
        fillColor: Colors.white.withOpacity(0.04),
        filled: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      ),
    );
  }
}

class InspectedPhoto {
  final File file;
  final double latitude;
  final double longitude;
  final String caption;
  InspectedPhoto({required this.file, required this.latitude, required this.longitude, required this.caption});
}
