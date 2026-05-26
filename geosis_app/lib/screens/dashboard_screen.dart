import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/odoo_service.dart';
import 'dart:ui';
import 'bitacora_history_screen.dart';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final odoo = OdooService();
  List<dynamic> projects = [];
  List<dynamic> bitacoras = [];
  bool isLoading = true;
  bool isLoadingBitacoras = true;
  int offlineReportsCount = 0;
  int offlineAvaluosCount = 0;
  bool isSyncing = false;
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadProjects();
    _loadOfflineCount();
  }

  Future<void> _loadOfflineCount() async {
    try {
      final drafts = await odoo.getOfflineReports();
      final avaluoDrafts = await odoo.getOfflineAvaluos();
      setState(() {
        offlineReportsCount = drafts.length;
        offlineAvaluosCount = avaluoDrafts.length;
      });
    } catch (e) {
      print("DEBUG: Error al cargar cantidad offline: $e");
    }
  }

  Future<void> _loadProjects() async {
    try {
      final data = await odoo.getProjects();
      final bitacoraList = await odoo.getBitacoras();
      setState(() {
        projects = data;
        bitacoras = bitacoraList;
        isLoading = false;
        isLoadingBitacoras = false;
      });
      _loadOfflineCount();
    } catch (e) {
      setState(() {
        isLoading = false;
        isLoadingBitacoras = false;
      });
    }
  }

  double _calculateProjectProgress(dynamic project) {
    final List<dynamic> tasks = project['tasks'] ?? [];
    if (tasks.isEmpty) return 0.0;
    double total = 0.0;
    for (var t in tasks) {
      total += (t['progress'] ?? 0.0);
    }
    return total / tasks.length;
  }

  String _getProjectEndDate(dynamic project) {
    final List<dynamic> tasks = project['tasks'] ?? [];
    if (tasks.isEmpty) return "En ejecución";
    String maxEnd = "";
    for (var t in tasks) {
      String end = t['end']?.toString() ?? "";
      if (end.isNotEmpty && (maxEnd.isEmpty || end.compareTo(maxEnd) > 0)) {
        maxEnd = end;
      }
    }
    return maxEnd.isNotEmpty ? maxEnd : "En ejecución";
  }

  Future<void> _syncOffline() async {
    setState(() => isSyncing = true);
    try {
      final results = await odoo.syncOfflineReports();
      final int success = results['success'] ?? 0;
      final int fail = results['fail'] ?? 0;

      final avResults = await odoo.syncOfflineAvaluos();
      final int avSuccess = avResults['success'] ?? 0;
      final int avFail = avResults['fail'] ?? 0;
      
      setState(() => isSyncing = false);
      _loadOfflineCount();

      final totalSuccess = success + avSuccess;
      final totalFail = fail + avFail;

      if (totalSuccess > 0 && totalFail == 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.greenAccent,
            content: Text("✅ Sincronizados $totalSuccess elementos ($success reportes, $avSuccess avalúos) correctamente con Odoo.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      } else if (totalSuccess > 0 && totalFail > 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.orangeAccent,
            content: Text("⚠️ Sincronizados $totalSuccess elementos, pero $totalFail fallaron. Inténtalo más tarde.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      } else if (totalFail > 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.redAccent,
            content: Text("❌ Falló la sincronización. Verifica tu conexión al servidor de Odoo.", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          )
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.cyanAccent,
            content: Text("ℹ️ No hay elementos offline pendientes por sincronizar.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      }
    } catch (e) {
      setState(() => isSyncing = false);
      print("DEBUG: Error en _syncOffline: $e");
    }
  }

  Widget _buildBody() {
    switch (_currentIndex) {
      case 0:
        return _buildDashboardTab();
      case 1:
        return _buildProjectsTab();
      case 2:
        return _buildReportsTab();
      case 3:
        return _buildTeamTab();
      case 4:
        return _buildProfileTab();
      default:
        return _buildDashboardTab();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Color(0xFF0D1B2E),
      body: Stack(
        children: [
          // FONDO ESTRUCTURAL (Igual a la imagen)
          Container(
            decoration: BoxDecoration(
              image: DecorationImage(
                image: NetworkImage('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1000'), 
                fit: BoxFit.cover,
              ),
            ),
          ),
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0xFF0D1B2E).withOpacity(0.8), Color(0xFF0D1B2E)],
              ),
            ),
          ),

          SafeArea(
            child: _buildBody(),
          ),
          if (isSyncing)
            Container(
              color: Colors.black87,
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(color: Colors.orangeAccent),
                    SizedBox(height: 20),
                    Text("Sincronizando reportes...", style: GoogleFonts.outfit(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                    SizedBox(height: 5),
                    Text("Subiendo borradores offline a Odoo...", style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12)),
                  ],
                ),
              ),
            ),
        ],
      ),
      bottomNavigationBar: _buildBottomNav(),
      floatingActionButton: _buildNeonFab(),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
    );
  }

  Widget _buildOfflineSyncCard() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: GestureDetector(
        onTap: _syncOffline,
        child: Container(
          padding: EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Colors.orangeAccent.withOpacity(0.08),
            borderRadius: BorderRadius.circular(25),
            border: Border.all(color: Colors.orangeAccent.withOpacity(0.4), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: Colors.orangeAccent.withOpacity(0.1),
                blurRadius: 10,
                spreadRadius: 1,
              )
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.orangeAccent.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.signal_wifi_off_outlined, color: Colors.orangeAccent, size: 28),
              ),
              SizedBox(width: 15),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Tienes $offlineReportsCount Reportes sin Enviar",
                      style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    SizedBox(height: 2),
                    Text(
                      "Te quedaste sin señal en la obra. Toca aquí para sincronizarlos con Odoo ahora.",
                      style: GoogleFonts.outfit(color: Colors.white70, fontSize: 11, height: 1.3),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios, color: Colors.orangeAccent, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGlassWeatherCard() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(25),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            padding: EdgeInsets.all(25),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(25),
              border: Border.all(color: Colors.white.withOpacity(0.1)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(Icons.wb_sunny, color: Colors.amber, size: 60),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text("28°C", style: GoogleFonts.outfit(color: Colors.white, fontSize: 38, fontWeight: FontWeight.bold)),
                    Text("Sunny | Cuenca, EC", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 14)),
                    Text("High 30°C / Low 21°C", style: GoogleFonts.outfit(color: Colors.white38, fontSize: 11)),
                  ],
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildProjectCard(dynamic project, String num, int index) {
    List<String> images = [
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=400',
      'https://images.unsplash.com/photo-1503387762-592dea58ef23?q=80&w=400',
      'https://images.unsplash.com/photo-1541888946425-d81bb19480c5?q=80&w=400'
    ];
    double progress = _calculateProjectProgress(project);
    return GestureDetector(
      onTap: () async {
        await Navigator.pushNamed(
          context, 
          '/form', 
          arguments: {
            'project_id': project['id'],
            'project_name': project['name'],
            'tasks': project['tasks'] ?? [],
          }
        );
        _loadOfflineCount();
      },
      child: Container(
        width: 190,
        margin: EdgeInsets.only(right: 15),
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(25),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 100,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(15),
                image: DecorationImage(image: NetworkImage(images[index % 3]), fit: BoxFit.cover),
              ),
              child: Align(
                alignment: Alignment.topLeft,
                child: Container(
                  margin: EdgeInsets.all(8),
                  padding: EdgeInsets.all(4),
                  decoration: BoxDecoration(color: Colors.black45, borderRadius: BorderRadius.circular(5)),
                  child: Text(num + ".", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                ),
              ),
            ),
            SizedBox(height: 12),
            Text(project['name'], maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.outfit(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold)),
            SizedBox(height: 5),
            Row(
              children: [
                Text("Estado: ", style: TextStyle(color: Colors.white38, fontSize: 10)),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(5)),
                  child: Text("Activo", style: TextStyle(color: Colors.greenAccent, fontSize: 9, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Progreso:", style: TextStyle(color: Colors.white38, fontSize: 10)),
                Text("${progress.toStringAsFixed(0)}%", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
              ],
            ),
            SizedBox(height: 5),
            LinearProgressIndicator(value: progress / 100.0, backgroundColor: Colors.white12, valueColor: AlwaysStoppedAnimation(Colors.cyanAccent), minHeight: 4),
            Spacer(),
            Text("Código: ${project['code']}", style: TextStyle(color: Colors.white24, fontSize: 9)),
            Text(project['location'] ?? "Sin ubicación", style: TextStyle(color: Colors.white38, fontSize: 9)),
          ],
        ),
      ),
    );
  }

  Widget _buildFeaturedProjectCard(String title, String num, String status, double progress, String dateRange) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15),
      child: Container(
        padding: EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.05),
          borderRadius: BorderRadius.circular(25),
        ),
        child: Row(
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(15),
                image: DecorationImage(image: NetworkImage('https://images.unsplash.com/photo-1541888946425-d81bb19480c5?q=80&w=400'), fit: BoxFit.cover),
              ),
            ),
            SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
                  Row(
                    children: [
                      Text("Estado: ", style: TextStyle(color: Colors.white38, fontSize: 10)),
                      Container(
                        padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(5)),
                        child: Text(status, style: TextStyle(color: Colors.orangeAccent, fontSize: 9, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                  SizedBox(height: 10),
                  LinearProgressIndicator(value: progress, backgroundColor: Colors.white12, valueColor: AlwaysStoppedAnimation(Colors.blueAccent), minHeight: 4),
                  SizedBox(height: 5),
                  Text("Fecha Fin: $dateRange", style: TextStyle(color: Colors.white38, fontSize: 10)),
                ],
              ),
            ),
            Text("${(progress * 100).toInt()}%", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
          ],
        ),
      ),
    );
  }

  Widget _buildSmallStatCard(String title, bool isChart) {
    return Container(
      padding: EdgeInsets.all(15),
      decoration: BoxDecoration(color: Colors.white.withOpacity(0.05), borderRadius: BorderRadius.circular(25)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
          SizedBox(height: 10),
          if (isChart) 
            Row(
              children: [
                _bar(20, Colors.cyanAccent), _bar(40, Colors.blueAccent), _bar(30, Colors.cyanAccent), _bar(50, Colors.blueAccent),
              ],
            )
          else
            Text("New Report", style: TextStyle(color: Colors.white54, fontSize: 12)),
        ],
      ),
    );
  }

  Widget _bar(double h, Color c) => Container(margin: EdgeInsets.only(right: 4), width: 4, height: h, color: c);

  Widget _buildBottomNav() {
    return Container(
      height: 80,
      color: Color(0xFF0D1B2E),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          GestureDetector(
            onTap: () => setState(() => _currentIndex = 0),
            child: _navIcon(Icons.home, "Dashboard", _currentIndex == 0),
          ),
          GestureDetector(
            onTap: () => setState(() => _currentIndex = 1),
            child: _navIcon(Icons.folder, "Projects", _currentIndex == 1),
          ),
          GestureDetector(
            onTap: () => setState(() => _currentIndex = 2),
            child: _navIcon(Icons.description, "Reports", _currentIndex == 2),
          ),
          GestureDetector(
            onTap: () => setState(() => _currentIndex = 3),
            child: _navIcon(Icons.people, "Team", _currentIndex == 3),
          ),
          GestureDetector(
            onTap: () => setState(() => _currentIndex = 4),
            child: _navIcon(Icons.person, "Profile", _currentIndex == 4),
          ),
        ],
      ),
    );
  }

  Widget _navIcon(IconData i, String l, bool s) => Column(
    mainAxisAlignment: MainAxisAlignment.center,
    children: [
      Icon(i, color: s ? Colors.cyanAccent : Colors.white30, size: 22),
      Text(l, style: TextStyle(color: s ? Colors.cyanAccent : Colors.white30, fontSize: 10)),
    ],
  );

  Widget _buildNeonFab() {
    return Container(
      height: 60, width: 60,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(colors: [Colors.blueAccent, Colors.cyanAccent]),
        boxShadow: [BoxShadow(color: Colors.cyanAccent.withOpacity(0.4), blurRadius: 15, spreadRadius: 2)],
      ),
      child: FloatingActionButton(
        onPressed: () => Navigator.pushNamed(context, '/form'),
        backgroundColor: Colors.transparent, elevation: 0,
        child: Icon(Icons.add, color: Colors.white, size: 30),
      ),
    );
  }

  // --- SUB-PÁGINAS GORGEOUS DE CADA TAB ---

  Widget _buildTabHeader(String title, String subtitle) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              children: [
                Icon(Icons.engineering, color: Colors.blueAccent, size: 24),
                SizedBox(width: 8),
                Text("GEOSIS", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
              ],
            ),
            Row(
              children: [
                Icon(Icons.notifications_none, color: Colors.white70, size: 26),
                SizedBox(width: 15),
                Icon(Icons.menu, color: Colors.white70, size: 26),
              ],
            )
          ],
        ),
        SizedBox(height: 25),
        Text(title, style: GoogleFonts.outfit(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold)),
        SizedBox(height: 5),
        Text(subtitle, style: GoogleFonts.outfit(color: Colors.white54, fontSize: 13)),
      ],
    );
  }

  Widget _buildSearchBar(String hint) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.04),
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
      ),
      child: TextField(
        style: TextStyle(color: Colors.white, fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: TextStyle(color: Colors.white24, fontSize: 13),
          prefixIcon: Icon(Icons.search, color: Colors.white30),
          border: InputBorder.none,
          contentPadding: EdgeInsets.symmetric(vertical: 15),
        ),
      ),
    );
  }

  Widget _buildDashboardTab() {
    final String featuredTitle = projects.isNotEmpty ? projects[0]['name'] : "Riverside Plaza";
    final double featuredProgressVal = projects.isNotEmpty ? _calculateProjectProgress(projects[0]) : 15.0;
    final int featuredTasksCount = projects.isNotEmpty ? (projects[0]['tasks']?.length ?? 0) : 3;
    final String featuredEndDate = projects.isNotEmpty ? _getProjectEndDate(projects[0]) : "2026-12-31";

    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(Icons.engineering, color: Colors.blueAccent, size: 24),
                    SizedBox(width: 8),
                    Text("GEOSIS", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
                  ],
                ),
                Row(
                  children: [
                    Icon(Icons.notifications_none, color: Colors.white70, size: 26),
                    SizedBox(width: 15),
                    Icon(Icons.menu, color: Colors.white70, size: 26),
                  ],
                )
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10),
            child: Row(
              children: [
                CircleAvatar(radius: 22, backgroundImage: NetworkImage('https://i.pravatar.cc/150?u=wendy')),
                SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text("Wendy L.", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                    Text("Directora de Obra", style: GoogleFonts.outfit(color: Colors.white54, fontSize: 12)),
                  ],
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Buenos Días,", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 24)),
                Text("Wendy", style: GoogleFonts.outfit(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
              ],
            ),
          ),
          _buildGlassWeatherCard(),
          if (offlineReportsCount > 0) ...[
            SizedBox(height: 20),
            _buildOfflineSyncCard(),
          ],
          if (offlineAvaluosCount > 0) ...[
            SizedBox(height: 20),
            _buildOfflineAvaluosSyncCard(),
          ],
          SizedBox(height: 25),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Text("Servicios de Campo", style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
          ),
          SizedBox(height: 15),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Row(
              children: [
                Expanded(
                  child: _buildServiceMenuCard(
                    title: "Libro de Obra",
                    subtitle: "Bitácoras Diarias",
                    icon: Icons.edit_note,
                    color: Colors.cyanAccent,
                    onTap: () {
                      setState(() {
                        _currentIndex = 2; // Cambia a la pestaña de reportes
                      });
                    },
                  ),
                ),
                SizedBox(width: 15),
                Expanded(
                  child: _buildServiceMenuCard(
                    title: "Avalúos",
                    subtitle: "Fichas de Campo",
                    icon: Icons.location_city,
                    color: Colors.blueAccent,
                    onTap: () {
                      Navigator.pushNamed(context, '/avaluos').then((_) => _loadOfflineCount());
                    },
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: 30),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Text("Mis Proyectos", style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
          ),
          SizedBox(height: 15),
          Container(
            height: 280,
            child: isLoading
            ? Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
            : ListView.builder(
                scrollDirection: Axis.horizontal,
                padding: EdgeInsets.only(left: 20),
                itemCount: projects.length,
                itemBuilder: (context, index) {
                  return _buildProjectCard(projects[index], (index + 1).toString(), index);
                },
              ),
          ),
          _buildFeaturedProjectCard(featuredTitle, featuredTasksCount.toString(), "Activo", featuredProgressVal / 100.0, featuredEndDate),
          SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20.0),
            child: Row(
              children: [
                Expanded(child: _buildSmallStatCard("Cronograma de Obra", true)),
                SizedBox(width: 15),
                Expanded(child: _buildSmallStatCard("Seguridad SSO", false)),
              ],
            ),
          ),
          SizedBox(height: 120),
        ],
      ),
    );
  }

  Widget _buildProjectsTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTabHeader("Proyectos Activos", "Gestión de contratos y obras asignadas"),
          SizedBox(height: 20),
          _buildSearchBar("Buscar proyecto contractual..."),
          SizedBox(height: 25),
          isLoading
          ? Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
          : Column(
              children: projects.map((project) {
                double progressVal = _calculateProjectProgress(project);
                String endDate = _getProjectEndDate(project);
                return Container(
                  margin: EdgeInsets.only(bottom: 20),
                  padding: EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.04),
                    borderRadius: BorderRadius.circular(25),
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
                              project['name'] ?? 'Proyecto sin Nombre',
                              style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
                            ),
                          ),
                          Container(
                            padding: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: Colors.cyanAccent.withOpacity(0.1),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              "Activo",
                              style: TextStyle(color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 10),
                      Text(
                        "${project['tasks']?.length ?? 0} Rubros Registrados",
                        style: TextStyle(color: Colors.white54, fontSize: 13),
                      ),
                      SizedBox(height: 15),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text("Progreso General", style: TextStyle(color: Colors.white38, fontSize: 12)),
                          Text("${progressVal.toStringAsFixed(0)}%", style: TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 12)),
                        ],
                      ),
                      SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: LinearProgressIndicator(
                          value: progressVal / 100.0,
                          backgroundColor: Colors.white10,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.cyanAccent),
                          minHeight: 6,
                        ),
                      ),
                      SizedBox(height: 20),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.calendar_today, color: Colors.white38, size: 14),
                              SizedBox(width: 5),
                              Text("Fecha Fin: $endDate", style: TextStyle(color: Colors.white38, fontSize: 11)),
                            ],
                          ),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.cyanAccent,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              padding: EdgeInsets.symmetric(horizontal: 15, vertical: 8),
                            ),
                            onPressed: () => Navigator.pushNamed(
                              context,
                              '/form',
                              arguments: {
                                'project_id': project['id'],
                                'project_name': project['name'],
                                'tasks': project['tasks'] ?? [],
                              }
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.add, color: Colors.black, size: 16),
                                SizedBox(width: 5),
                                Text("Bitácora", style: GoogleFonts.outfit(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }

  Widget _buildReportsTab() {
    final recentBitacoras = bitacoras.take(5).toList();

    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTabHeader("Libro de Obra", "Historial de asientos y reportes diarios"),
          SizedBox(height: 25),
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [Colors.blueAccent.withOpacity(0.15), Colors.cyanAccent.withOpacity(0.05)]),
              borderRadius: BorderRadius.circular(25),
              border: Border.all(color: Colors.cyanAccent.withOpacity(0.2)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text("Total Asientos", style: TextStyle(color: Colors.white70, fontSize: 13)),
                      SizedBox(height: 5),
                      Text("${bitacoras.length} Reportes", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 22)),
                    ],
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.cyanAccent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => Navigator.pushNamed(context, '/history'),
                  child: Text("Ver Historial", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 12)),
                )
              ],
            ),
          ),
          SizedBox(height: 25),
          Text("Asientos Recientes", style: GoogleFonts.outfit(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          SizedBox(height: 15),
          isLoadingBitacoras
          ? Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
          : recentBitacoras.isEmpty
            ? Container(
                padding: EdgeInsets.all(20),
                decoration: BoxDecoration(color: Colors.white.withOpacity(0.02), borderRadius: BorderRadius.circular(20)),
                child: Center(
                  child: Text("No hay reportes registrados aún en Odoo.", style: TextStyle(color: Colors.white38, fontSize: 12)),
                ),
              )
            : Column(
                children: recentBitacoras.map((b) {
                  final String dateStr = b['date'] ?? '';
                  final String weather = b['weather'] ?? 'sunny';
                  final String summary = b['content'] ?? 'Sin observaciones del residente.';
                  final String status = b['state'] == 'approved' ? 'Aprobado' : 'Borrador';
                  final String title = "Asiento Diario";
                  
                  String weatherEsp = "Soleado";
                  if (weather == "cloudy") weatherEsp = "Nublado";
                  else if (weather == "rainy") weatherEsp = "Lluvia";
                  else if (weather == "storm") weatherEsp = "Tormenta";

                  return GestureDetector(
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => BitacoraDetailScreen(bitacora: b),
                        ),
                      );
                    },
                    child: _buildReportHistoryItem(title, dateStr, weatherEsp, summary, status),
                  );
                }).toList(),
              ),
        ],
      ),
    );
  }

  Widget _buildReportHistoryItem(String title, String date, String weather, String summary, String status) {
    return Container(
      margin: EdgeInsets.only(bottom: 15),
      padding: EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.04)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.greenAccent.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  status,
                  style: TextStyle(color: Colors.greenAccent, fontSize: 9, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
          SizedBox(height: 5),
          Row(
            children: [
              Icon(Icons.calendar_today, color: Colors.white38, size: 12),
              SizedBox(width: 5),
              Text(date, style: TextStyle(color: Colors.white38, fontSize: 11)),
              SizedBox(width: 15),
              Icon(Icons.wb_sunny, color: Colors.amber, size: 12),
              SizedBox(width: 5),
              Text(weather, style: TextStyle(color: Colors.white38, fontSize: 11)),
            ],
          ),
          SizedBox(height: 10),
          Text(summary, style: TextStyle(color: Colors.white70, fontSize: 13, height: 1.3)),
        ],
      ),
    );
  }

  Widget _buildTeamTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTabHeader("Equipo de Trabajo", "Personal de fiscalización, residencia y obra"),
          SizedBox(height: 20),
          _buildSearchBar("Buscar miembro del equipo..."),
          SizedBox(height: 25),
          _buildTeamMemberCard("Wendy Llivichuzhca", "Residente de Obra / Directora", "Riverside Plaza", "https://i.pravatar.cc/150?u=wendy"),
          _buildTeamMemberCard("Ing. Carlos Andrade", "Fiscalizador / Supervisor MIDUVI", "Fiscalización GAD", "https://i.pravatar.cc/150?u=carlos"),
          _buildTeamMemberCard("Arq. Sofía Méndez", "Representante del Contratista", "Riverside Plaza", "https://i.pravatar.cc/150?u=sofia"),
          _buildTeamMemberCard("Ing. Pedro Torres", "Inspector de Seguridad y SSO", "Riverside Plaza", "https://i.pravatar.cc/150?u=pedro"),
        ],
      ),
    );
  }

  Widget _buildTeamMemberCard(String name, String role, String project, String avatarUrl) {
    return Container(
      margin: EdgeInsets.only(bottom: 15),
      padding: EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.04)),
      ),
      child: Row(
        children: [
          CircleAvatar(radius: 26, backgroundImage: NetworkImage(avatarUrl)),
          SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15)),
                SizedBox(height: 2),
                Text(role, style: TextStyle(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.w500)),
                SizedBox(height: 5),
                Row(
                  children: [
                    Icon(Icons.business_center_outlined, color: Colors.white38, size: 12),
                    SizedBox(width: 5),
                    Text(project, style: TextStyle(color: Colors.white38, fontSize: 11)),
                  ],
                ),
              ],
            ),
          ),
          Row(
            children: [
              _circleActionButton(Icons.phone, Colors.blueAccent),
              SizedBox(width: 8),
              _circleActionButton(Icons.message, Colors.greenAccent),
            ],
          ),
        ],
      ),
    );
  }

  Widget _circleActionButton(IconData icon, Color color) {
    return Container(
      padding: EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        shape: BoxShape.circle,
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Icon(icon, color: color, size: 16),
    );
  }

  Widget _buildProfileTab() {
    return SingleChildScrollView(
      physics: BouncingScrollPhysics(),
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildTabHeader("Mi Perfil", "Configuración de cuenta y sincronización ERP"),
          SizedBox(height: 25),
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.03),
              borderRadius: BorderRadius.circular(25),
              border: Border.all(color: Colors.white.withOpacity(0.04)),
            ),
            child: Column(
              children: [
                Center(
                  child: Stack(
                    children: [
                      Container(
                        padding: EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.cyanAccent, width: 2),
                        ),
                        child: CircleAvatar(radius: 40, backgroundImage: NetworkImage('https://i.pravatar.cc/150?u=wendy')),
                      ),
                      Positioned(
                        bottom: 0, right: 0,
                        child: Container(
                          padding: EdgeInsets.all(6),
                          decoration: BoxDecoration(color: Colors.greenAccent, shape: BoxShape.circle),
                          child: Icon(Icons.check, color: Colors.black, size: 12),
                        ),
                      )
                    ],
                  ),
                ),
                SizedBox(height: 15),
                Text("Wendy Llivichuzhca", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18)),
                Text("Residente de Obra / Administradora", style: TextStyle(color: Colors.white54, fontSize: 12)),
                SizedBox(height: 10),
                Chip(
                  backgroundColor: Colors.blueAccent.withOpacity(0.1),
                  label: Text("GEOSIS-PRO ERP", style: TextStyle(color: Colors.cyanAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                )
              ],
            ),
          ),
          SizedBox(height: 25),
          Text("Servidor Odoo ERP", style: GoogleFonts.outfit(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
          SizedBox(height: 12),
          Container(
            padding: EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.02),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: Colors.white.withOpacity(0.03)),
            ),
            child: Column(
              children: [
                _profileDetailRow("Instancia URL", "geosis.corporativoqbank.com"),
                Divider(color: Colors.white10, height: 25),
                _profileDetailRow("Base de Datos", "odoo-final"),
                Divider(color: Colors.white10, height: 25),
                _profileDetailRow("Estado", "Conectado", isStatus: true),
              ],
            ),
          ),
          SizedBox(height: 25),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent.withOpacity(0.1),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                side: BorderSide(color: Colors.redAccent.withOpacity(0.5)),
              ),
              onPressed: () {
                Navigator.pushReplacementNamed(context, '/login');
              },
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.logout, color: Colors.redAccent, size: 18),
                  SizedBox(width: 8),
                  Text("CERRAR SESIÓN", style: GoogleFonts.outfit(color: Colors.redAccent, fontWeight: FontWeight.bold, fontSize: 14)),
                ],
              ),
            ),
          ),
          SizedBox(height: 30),
        ],
      ),
    );
  }

  Widget _profileDetailRow(String label, String value, {bool isStatus = false}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: Colors.white38, fontSize: 13)),
        Row(
          children: [
            if (isStatus) ...[
              Container(width: 8, height: 8, decoration: BoxDecoration(color: Colors.greenAccent, shape: BoxShape.circle)),
              SizedBox(width: 8),
            ],
            Text(value, style: TextStyle(color: isStatus ? Colors.greenAccent : Colors.white70, fontSize: 13, fontWeight: FontWeight.w500)),
          ],
        ),
      ],
    );
  }

  Widget _buildOfflineAvaluosSyncCard() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20.0),
      child: GestureDetector(
        onTap: _syncOffline,
        child: Container(
          padding: EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: Colors.orangeAccent.withOpacity(0.08),
            borderRadius: BorderRadius.circular(25),
            border: Border.all(color: Colors.orangeAccent.withOpacity(0.4), width: 1.5),
            boxShadow: [
              BoxShadow(
                color: Colors.orangeAccent.withOpacity(0.1),
                blurRadius: 10,
                spreadRadius: 1,
              )
            ],
          ),
          child: Row(
            children: [
              Container(
                padding: EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.orangeAccent.withOpacity(0.2),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.signal_wifi_off_outlined, color: Colors.orangeAccent, size: 28),
              ),
              SizedBox(width: 15),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      "Tienes $offlineAvaluosCount Avalúos sin Enviar",
                      style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    SizedBox(height: 2),
                    Text(
                      "Inspecciones guardadas en campo sin señal. Toca aquí para sincronizar con Odoo ahora.",
                      style: GoogleFonts.outfit(color: Colors.white70, fontSize: 11, height: 1.3),
                    ),
                  ],
                ),
              ),
              Icon(Icons.arrow_forward_ios, color: Colors.orangeAccent, size: 16),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildServiceMenuCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Colors.white.withOpacity(0.04),
          borderRadius: BorderRadius.circular(25),
          border: Border.all(color: Colors.white.withOpacity(0.06)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withOpacity(0.15),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 24),
            ),
            SizedBox(height: 15),
            Text(title, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
            SizedBox(height: 2),
            Text(subtitle, style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
