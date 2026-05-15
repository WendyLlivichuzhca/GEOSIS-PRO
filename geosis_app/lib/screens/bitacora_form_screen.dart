import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class BitacoraFormScreen extends StatefulWidget {
  @override
  _BitacoraFormScreenState createState() => _BitacoraFormScreenState();
}

class _BitacoraFormScreenState extends State<BitacoraFormScreen> {
  String selectedWeather = 'sunny';
  List<Map<String, dynamic>> tasks = [
    {'name': 'Excavación de cimientos', 'progress': 100, 'done': true},
    {'name': 'Armado de columnas', 'progress': 45, 'done': false},
    {'name': 'Instalación eléctrica', 'progress': 10, 'done': false},
  ];

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
      body: SingleChildScrollView(
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
                TextButton(onPressed: () {}, child: Text("+ Agregar Tarea", style: TextStyle(color: Colors.blueAccent))),
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
                  _buildAddPhotoBtn(),
                  _buildPhotoItem('https://via.placeholder.com/150'),
                  _buildPhotoItem('https://via.placeholder.com/151'),
                ],
              ),
            ),

            SizedBox(height: 50),
            // BOTON GUARDAR
            SizedBox(
              width: double.infinity,
              height: 60,
              child: ElevatedButton(
                onPressed: () {
                  // Lógica para enviar a Odoo
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.greenAccent[700],
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                ),
                child: Text("GUARDAR Y SINCRONIZAR", style: GoogleFonts.outfit(fontWeight: FontWeight.bold, fontSize: 18, color: Colors.white)),
              ),
            ),
          ],
        ),
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
              color: isSelected ? Colors.blueAccent : Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: isSelected ? Colors.blueAccent : Colors.white10),
            ),
            child: Icon(icon, color: isSelected ? Colors.white : Colors.white38),
          ),
          SizedBox(height: 5),
          Text(label, style: TextStyle(color: isSelected ? Colors.white : Colors.white38, fontSize: 10)),
        ],
      ),
    );
  }

  Widget _buildTaskItem(Map<String, dynamic> task) {
    return Container(
      margin: EdgeInsets.only(bottom: 15),
      padding: EdgeInsets.all(15),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.03), borderRadius: BorderRadius.circular(15)),
      child: Column(
        children: [
          Row(
            children: [
              Checkbox(
                value: task['done'],
                onChanged: (val) => setState(() => task['done'] = val),
                activeColor: Colors.blueAccent,
                side: BorderSide(color: Colors.white24),
              ),
              Expanded(child: Text(task['name'], style: TextStyle(color: Colors.white, fontWeight: FontWeight.w500))),
              Text("${task['progress']}%", style: TextStyle(color: Colors.white54, fontSize: 12)),
            ],
          ),
          Slider(
            value: task['progress'].toDouble(),
            min: 0, max: 100,
            activeColor: Colors.blueAccent,
            inactiveColor: Colors.white10,
            onChanged: (val) => setState(() => task['progress'] = val.toInt()),
          ),
        ],
      ),
    );
  }

  Widget _buildAddPhotoBtn() {
    return Container(
      width: 100,
      margin: EdgeInsets.only(right: 15),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white10, style: BorderStyle.solid),
      ),
      child: Icon(Icons.add_a_photo_outlined, color: Colors.blueAccent),
    );
  }

  Widget _buildPhotoItem(String url) {
    return Container(
      width: 100,
      margin: EdgeInsets.only(right: 15),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15),
        image: DecorationImage(image: NetworkImage(url), fit: BoxFit.cover),
      ),
    );
  }
}
