import 'dart:convert';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/odoo_service.dart';

class BitacoraHistoryScreen extends StatefulWidget {
  @override
  _BitacoraHistoryScreenState createState() => _BitacoraHistoryScreenState();
}

class _BitacoraHistoryScreenState extends State<BitacoraHistoryScreen> {
  final odoo = OdooService();
  List<dynamic> bitacoras = [];
  List<dynamic> filteredBitacoras = [];
  List<dynamic> projects = [];
  int? selectedProjectId;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => isLoading = true);
    try {
      final bitacoraList = await odoo.getBitacoras();
      final projectList = await odoo.getProjects();
      setState(() {
        bitacoras = bitacoraList;
        filteredBitacoras = bitacoraList;
        projects = projectList;
        isLoading = false;
      });
    } catch (e) {
      print("DEBUG: Error al cargar datos del historial: $e");
      setState(() => isLoading = false);
    }
  }

  void _filterByProject(int? projectId) {
    setState(() {
      selectedProjectId = projectId;
      if (projectId == null) {
        filteredBitacoras = bitacoras;
      } else {
        filteredBitacoras = bitacoras.where((b) => b['project_id'] == projectId).toList();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFF0D1B2E),
      appBar: AppBar(
        backgroundColor: Color(0xFF0D1B2E),
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          "Historial Libro de Obra",
          style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
        ),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh, color: Colors.cyanAccent),
            onPressed: _loadData,
          )
        ],
      ),
      body: Stack(
        children: [
          // Fondo estructural difuminado
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0D1B2E), Color(0xFF081220)],
              ),
            ),
          ),
          
          SafeArea(
            child: isLoading
                ? Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
                : Column(
                    children: [
                      // Selector de Proyectos (Chips horizontales premium)
                      _buildProjectFilterSelector(),
                      
                      // Listado de Bitácoras
                      Expanded(
                        child: filteredBitacoras.isEmpty
                            ? _buildEmptyState()
                            : ListView.builder(
                                physics: BouncingScrollPhysics(),
                                padding: EdgeInsets.all(20),
                                itemCount: filteredBitacoras.length,
                                itemBuilder: (context, index) {
                                  return _buildBitacoraCard(filteredBitacoras[index]);
                                },
                              ),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  // 1. SELECTOR DE FILTRO DE PROYECTOS
  Widget _buildProjectFilterSelector() {
    return Container(
      height: 55,
      padding: EdgeInsets.symmetric(vertical: 8),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.only(left: 20),
        itemCount: projects.length + 1,
        itemBuilder: (context, index) {
          final isAll = index == 0;
          final project = isAll ? null : projects[index - 1];
          final projectId = isAll ? null : project['id'];
          final projectName = isAll ? "Todos los Proyectos" : project['name'];
          final isSelected = selectedProjectId == projectId;

          return GestureDetector(
            onTap: () => _filterByProject(projectId),
            child: Container(
              margin: EdgeInsets.only(right: 12),
              padding: EdgeInsets.symmetric(horizontal: 18, vertical: 8),
              decoration: BoxDecoration(
                gradient: isSelected
                    ? LinearGradient(colors: [Colors.blueAccent, Colors.cyanAccent])
                    : null,
                color: isSelected ? null : Colors.white.withOpacity(0.05),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isSelected ? Colors.cyanAccent.withOpacity(0.5) : Colors.white.withOpacity(0.1),
                ),
              ),
              child: Center(
                child: Text(
                  projectName,
                  style: GoogleFonts.outfit(
                    color: isSelected ? Colors.white : Colors.white70,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  // 2. VISTA CUANDO NO HAY REGISTROS
  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.assignment_late_outlined, size: 80, color: Colors.white24),
          SizedBox(height: 15),
          Text(
            "No hay reportes diarios registrados",
            style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 5),
          Text(
            "Los reportes de obra aparecerán aquí una vez sincronizados.",
            textAlign: TextAlign.center,
            style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12),
          ),
        ],
      ),
    );
  }

  // 3. TARJETA INDIVIDUAL DE BITÁCORA (VISTA RESUMIDA)
  Widget _buildBitacoraCard(dynamic bitacora) {
    final bool isApproved = bitacora['state'] == 'approved';
    final String dateStr = bitacora['date'] ?? '';
    final String weather = bitacora['weather'] ?? 'sunny';
    
    IconData weatherIcon = Icons.wb_sunny;
    Color weatherColor = Colors.amber;
    if (weather == 'cloudy') {
      weatherIcon = Icons.wb_cloudy_outlined;
      weatherColor = Colors.grey;
    } else if (weather == 'rainy') {
      weatherIcon = Icons.umbrella_outlined;
      weatherColor = Colors.blueAccent;
    } else if (weather == 'storm') {
      weatherIcon = Icons.flash_on;
      weatherColor = Colors.redAccent;
    }

    return GestureDetector(
      onTap: () => _openBitacoraDetailScreen(bitacora),
      child: Container(
        margin: EdgeInsets.only(bottom: 16),
        padding: EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(25),
          border: Border.all(color: Colors.white.withOpacity(0.08)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cabecera: Fecha y Estado
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(weatherIcon, color: weatherColor, size: 22),
                    SizedBox(width: 8),
                    Text(
                      dateStr,
                      style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                    ),
                  ],
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: isApproved ? Colors.green.withOpacity(0.15) : Colors.orange.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: isApproved ? Colors.greenAccent : Colors.orangeAccent,
                      width: 1,
                    ),
                  ),
                  child: Text(
                    isApproved ? "APROBADO" : "BORRADOR",
                    style: GoogleFonts.outfit(
                      color: isApproved ? Colors.greenAccent : Colors.orangeAccent,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            
            SizedBox(height: 12),
            // Proyecto
            Text(
              bitacora['project_name'] ?? 'Proyecto sin Nombre',
              style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.w600, fontSize: 14),
            ),
            SizedBox(height: 8),
            
            // Preview de Contenido
            Text(
              bitacora['content'] != null && bitacora['content'].toString().isNotEmpty
                  ? bitacora['content']
                  : 'Sin observaciones del residente.',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: GoogleFonts.outfit(color: Colors.white70, fontSize: 12),
            ),
            
            SizedBox(height: 15),
            Divider(color: Colors.white10),
            SizedBox(height: 5),
            
            // Footer: Cantidad de rubros reportados y fotos
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.engineering, size: 16, color: Colors.white38),
                    SizedBox(width: 5),
                    Text(
                      "${bitacora['tasks']?.length ?? 0} Rubros",
                      style: GoogleFonts.outfit(color: Colors.white54, fontSize: 11),
                    ),
                    SizedBox(width: 15),
                    Icon(Icons.camera_alt, size: 16, color: Colors.white38),
                    SizedBox(width: 5),
                    Text(
                      "${bitacora['photos']?.length ?? 0} Fotos",
                      style: GoogleFonts.outfit(color: Colors.white54, fontSize: 11),
                    ),
                  ],
                ),
                Text(
                  "Ver detalle →",
                  style: GoogleFonts.outfit(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.bold),
                )
              ],
            )
          ],
        ),
      ),
    );
  }

  // 4. VER PANTALLA DETALLADA DEL REPORTE DIARIO (Estilo MIDUVI)
  void _openBitacoraDetailScreen(dynamic bitacora) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => BitacoraDetailScreen(bitacora: bitacora),
      ),
    );
  }
}

// ----------------------------------------------------
// PANTALLA DE DETALLE DE BITÁCORA (FICHA MIDUVI LEÍBLE)
// ----------------------------------------------------
class BitacoraDetailScreen extends StatelessWidget {
  final dynamic bitacora;

  BitacoraDetailScreen({required this.bitacora});

  @override
  Widget build(BuildContext context) {
    final bool isApproved = bitacora['state'] == 'approved';
    final String dateStr = bitacora['date'] ?? '';
    final String weather = bitacora['weather'] ?? 'sunny';
    
    IconData weatherIcon = Icons.wb_sunny;
    Color weatherColor = Colors.amber;
    if (weather == 'cloudy') {
      weatherIcon = Icons.wb_cloudy_outlined;
      weatherColor = Colors.grey;
    } else if (weather == 'rainy') {
      weatherIcon = Icons.umbrella_outlined;
      weatherColor = Colors.blueAccent;
    } else if (weather == 'storm') {
      weatherIcon = Icons.flash_on;
      weatherColor = Colors.redAccent;
    }

    return Scaffold(
      backgroundColor: Color(0xFF0D1B2E),
      appBar: AppBar(
        backgroundColor: Color(0xFF0D1B2E),
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          "Ficha Libro de Obra",
          style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
        ),
      ),
      body: Stack(
        children: [
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0D1B2E), Color(0xFF081220)],
              ),
            ),
          ),
          
          SafeArea(
            child: SingleChildScrollView(
              physics: BouncingScrollPhysics(),
              padding: EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // CABECERA: Proyecto y Fecha
                  Container(
                    width: double.infinity,
                    padding: EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.04),
                      borderRadius: BorderRadius.circular(25),
                      border: Border.all(color: Colors.white.withOpacity(0.06)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              "REPORTE DIARIO",
                              style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1.5),
                            ),
                            Container(
                              padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: isApproved ? Colors.green.withOpacity(0.15) : Colors.orange.withOpacity(0.15),
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(
                                  color: isApproved ? Colors.greenAccent : Colors.orangeAccent,
                                  width: 1,
                                ),
                              ),
                              child: Text(
                                isApproved ? "APROBADO" : "PENDIENTE",
                                style: GoogleFonts.outfit(
                                  color: isApproved ? Colors.greenAccent : Colors.orangeAccent,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        SizedBox(height: 8),
                        Text(
                          bitacora['project_name'] ?? 'Proyecto sin Nombre',
                          style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
                        ),
                        SizedBox(height: 12),
                        Divider(color: Colors.white10),
                        SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Row(
                              children: [
                                Icon(Icons.calendar_today, size: 16, color: Colors.white54),
                                SizedBox(width: 6),
                                Text(dateStr, style: GoogleFonts.outfit(color: Colors.white70, fontSize: 13)),
                              ],
                            ),
                            Row(
                              children: [
                                Icon(weatherIcon, size: 18, color: weatherColor),
                                SizedBox(width: 6),
                                Text(
                                  weather == 'sunny' ? 'SOLEADO' :
                                  weather == 'cloudy' ? 'NUBLADO' :
                                  weather == 'rainy' ? 'LLUVIA' :
                                  weather == 'storm' ? 'TORMENTA' : weather.toUpperCase(),
                                  style: GoogleFonts.outfit(color: Colors.white70, fontSize: 13, fontWeight: FontWeight.w600),
                                ),
                              ],
                            )
                          ],
                        )
                      ],
                    ),
                  ),
                  
                  SizedBox(height: 25),
                  
                  // SECCIÓN: Mano de Obra y Equipos (Recursos)
                  Text("Recursos Utilizados", style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 15)),
                  SizedBox(height: 12),
                  
                  _buildGlassCard(
                    title: "Personal en Obra (Residente/Mano de Obra)",
                    icon: Icons.people,
                    content: bitacora['personal_notes'],
                  ),
                  SizedBox(height: 12),
                  _buildGlassCard(
                    title: "Equipos y Maquinaria Activa",
                    icon: Icons.local_shipping,
                    content: bitacora['equipment_notes'],
                  ),
                  
                  SizedBox(height: 25),
                  
                  // SECCIÓN: Novedades / Consultas del Contratista
                  Text("Requerimientos y Consultas", style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 15)),
                  SizedBox(height: 12),
                  _buildGlassCard(
                    title: "Consultas presentadas por el Residente",
                    icon: Icons.help_outline,
                    content: bitacora['contractor_queries'],
                    color: Colors.blueAccent.withOpacity(0.08),
                  ),

                  SizedBox(height: 25),

                  // SECCIÓN: Tareas / Rubros Reportados
                  Text("Avance de Rubros", style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 15)),
                  SizedBox(height: 12),
                  _buildTasksList(),
                  
                  SizedBox(height: 25),
                  
                  // SECCIÓN: Evidencia Fotográfica
                  Text("Evidencias de Obra", style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 15)),
                  SizedBox(height: 12),
                  _buildPhotosGallery(),

                  SizedBox(height: 25),
                  
                  // SECCIÓN: Firma del Residente (Contratista)
                  Text("Firmas del Acta Diario", style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 15)),
                  SizedBox(height: 12),
                  _buildSignaturesZone(),
                  
                  SizedBox(height: 40),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  // WIDGET CARD DE CRISTAL COMPONIBLE
  Widget _buildGlassCard({required String title, required IconData icon, String? content, Color? color}) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color ?? Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: Colors.cyanAccent, size: 18),
              SizedBox(width: 8),
              Text(
                title,
                style: GoogleFonts.outfit(color: Colors.white70, fontWeight: FontWeight.bold, fontSize: 12),
              ),
            ],
          ),
          SizedBox(height: 10),
          Text(
            content != null && content.trim().isNotEmpty ? content : "Ninguna novedad registrada en el sistema.",
            style: GoogleFonts.outfit(color: Colors.white, fontSize: 13, height: 1.4),
          )
        ],
      ),
    );
  }

  // VISTA DE LISTADO DE RUBROS REPORTADOS
  Widget _buildTasksList() {
    final List<dynamic> tasks = bitacora['tasks'] ?? [];
    if (tasks.isEmpty) {
      return Container(
        padding: EdgeInsets.all(15),
        decoration: BoxDecoration(color: Colors.white.withOpacity(0.02), borderRadius: BorderRadius.circular(20)),
        child: Center(
          child: Text("No se registraron avances específicos en este día.", style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12)),
        ),
      );
    }

    return Column(
      children: tasks.map<Widget>((t) {
        final int prog = t['progress'] ?? 0;
        return Container(
          margin: EdgeInsets.only(bottom: 12),
          padding: EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.03),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: Colors.white.withOpacity(0.05)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      t['task_name'] ?? 'Rubro APU',
                      style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                  ),
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.cyan.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      "$prog%",
                      style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11),
                    ),
                  )
                ],
              ),
              SizedBox(height: 10),
              LinearProgressIndicator(
                value: prog / 100.0,
                backgroundColor: Colors.white10,
                valueColor: AlwaysStoppedAnimation(Colors.cyanAccent),
                minHeight: 4,
              ),
              if (t['notes'] != null && t['notes'].toString().isNotEmpty) ...[
                SizedBox(height: 10),
                Text(
                  "Observación: ${t['notes']}",
                  style: GoogleFonts.outfit(color: Colors.white54, fontSize: 11, fontStyle: FontStyle.italic),
                )
              ]
            ],
          ),
        );
      }).toList(),
    );
  }

  // GALERÍA DE FOTOS
  Widget _buildPhotosGallery() {
    final List<dynamic> photos = bitacora['photos'] ?? [];
    if (photos.isEmpty) {
      return Container(
        padding: EdgeInsets.all(15),
        decoration: BoxDecoration(color: Colors.white.withOpacity(0.02), borderRadius: BorderRadius.circular(20)),
        child: Center(
          child: Text("Sin registros fotográficos.", style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12)),
        ),
      );
    }

    return Container(
      height: 130,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: photos.length,
        itemBuilder: (context, index) {
          final photo = photos[index];
          final String base64Img = photo['image'] ?? '';
          
          return Container(
            margin: EdgeInsets.only(right: 12),
            width: 140,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: Colors.white10),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(15),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  base64Img.isNotEmpty
                      ? Image.memory(
                          base64Decode(base64Img),
                          fit: BoxFit.cover,
                        )
                      : Container(color: Colors.grey[900], child: Icon(Icons.broken_image, color: Colors.white24)),
                  if (photo['caption'] != null && photo['caption'].toString().isNotEmpty)
                    Positioned(
                      bottom: 0, left: 0, right: 0,
                      child: Container(
                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        color: Colors.black54,
                        child: Text(
                          photo['caption'],
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.outfit(color: Colors.white70, fontSize: 9),
                        ),
                      ),
                    )
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ZONA DE FIRMA CON EL RESIDENTE Y FISCALIZADOR
  Widget _buildSignaturesZone() {
    final String contractorSig = bitacora['signature_contractor'] ?? '';
    final String inspectorSig = bitacora['signature_inspector'] ?? '';
    final String inspectorNotes = bitacora['inspector_instructions'] ?? '';

    return Column(
      children: [
        Row(
          children: [
            // FIRMA DEL RESIDENTE
            Expanded(
              child: Column(
                children: [
                  Text(
                    "Residente (Contratista)",
                    style: GoogleFonts.outfit(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Container(
                    height: 100,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: Colors.white10),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(15),
                      child: contractorSig.isNotEmpty
                          ? Image.memory(base64Decode(contractorSig), fit: BoxFit.contain)
                          : Center(child: Text("Sin firma", style: GoogleFonts.outfit(color: Colors.black38, fontSize: 12))),
                    ),
                  )
                ],
              ),
            ),
            
            SizedBox(width: 15),

            // FIRMA DEL FISCALIZADOR
            Expanded(
              child: Column(
                children: [
                  Text(
                    "Fiscalizador (Aprobador)",
                    style: GoogleFonts.outfit(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 8),
                  Container(
                    height: 100,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: inspectorSig.isNotEmpty ? Colors.white : Colors.white.withOpacity(0.02),
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(
                        color: inspectorSig.isNotEmpty ? Colors.white10 : Colors.orangeAccent.withOpacity(0.2),
                      ),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(15),
                      child: inspectorSig.isNotEmpty
                          ? Image.memory(base64Decode(inspectorSig), fit: BoxFit.contain)
                          : Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.hourglass_empty, size: 20, color: Colors.orangeAccent),
                                  SizedBox(height: 4),
                                  Text(
                                    "Pendiente Aprobación",
                                    textAlign: TextAlign.center,
                                    style: GoogleFonts.outfit(color: Colors.orangeAccent, fontSize: 9, fontWeight: FontWeight.w600),
                                  ),
                                ],
                              ),
                            ),
                    ),
                  )
                ],
              ),
            )
          ],
        ),

        // SI HAY RESPUESTA U OBSERVACIONES DEL FISCALIZADOR, MOSTRAR PANEL DESTACADO
        if (inspectorNotes.isNotEmpty) ...[
          SizedBox(height: 20),
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.withOpacity(0.08),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.greenAccent.withOpacity(0.2)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.security_update_good, color: Colors.greenAccent, size: 18),
                    SizedBox(width: 8),
                    Text(
                      "Instrucción Oficial de Fiscalización",
                      style: GoogleFonts.outfit(color: Colors.greenAccent, fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  inspectorNotes,
                  style: GoogleFonts.outfit(color: Colors.white, fontSize: 13, height: 1.4),
                )
              ],
            ),
          )
        ],
      ],
    );
  }
}
