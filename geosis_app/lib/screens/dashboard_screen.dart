import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/odoo_service.dart';
import 'dart:ui';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final odoo = OdooService();
  List<dynamic> projects = [];
  bool isLoading = true;
  int offlineReportsCount = 0;
  bool isSyncing = false;

  @override
  void initState() {
    super.initState();
    _loadProjects();
    _loadOfflineCount();
  }

  Future<void> _loadOfflineCount() async {
    try {
      final drafts = await odoo.getOfflineReports();
      setState(() {
        offlineReportsCount = drafts.length;
      });
    } catch (e) {
      print("DEBUG: Error al cargar cantidad offline: $e");
    }
  }

  Future<void> _loadProjects() async {
    try {
      final data = await odoo.getProjects();
      setState(() {
        projects = data;
        isLoading = false;
      });
      _loadOfflineCount();
    } catch (e) {
      setState(() => isLoading = false);
    }
  }

  Future<void> _syncOffline() async {
    setState(() => isSyncing = true);
    try {
      final results = await odoo.syncOfflineReports();
      final int success = results['success'] ?? 0;
      final int fail = results['fail'] ?? 0;
      
      setState(() => isSyncing = false);
      _loadOfflineCount();

      if (success > 0 && fail == 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.greenAccent,
            content: Text("✅ Sincronizados $success reportes correctamente con Odoo.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      } else if (success > 0 && fail > 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            backgroundColor: Colors.orangeAccent,
            content: Text("⚠️ Sincronizados $success reportes, pero $fail fallaron. Inténtalo más tarde.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      } else if (fail > 0) {
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
            content: Text("ℹ️ No hay reportes offline pendientes por sincronizar.", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          )
        );
      }
    } catch (e) {
      setState(() => isSyncing = false);
      print("DEBUG: Error en _syncOffline: $e");
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
            child: SingleChildScrollView(
              physics: BouncingScrollPhysics(),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. TOP BAR (LOGO GEOSIS Y PERFIL)
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

                  // PERFIL
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
                            Text("Site Manager", style: GoogleFonts.outfit(color: Colors.white54, fontSize: 12)),
                          ],
                        ),
                      ],
                    ),
                  ),

                  // SALUDO
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 15),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Good Morning,", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 24)),
                        Text("Wendy", style: GoogleFonts.outfit(color: Colors.white, fontSize: 32, fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ),

                  // WEATHER CARD (PERFECTA)
                  _buildGlassWeatherCard(),

                  if (offlineReportsCount > 0) ...[
                    SizedBox(height: 20),
                    _buildOfflineSyncCard(),
                  ],

                  SizedBox(height: 30),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20.0),
                    child: Text("My Projects", style: GoogleFonts.outfit(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
                  ),
                  SizedBox(height: 15),

                  // CAROUSEL DE PROYECTOS
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

                  // PROYECTO DESTACADO HORIZONTAL (Riverside Plaza)
                  _buildFeaturedProjectCard("Riverside Plaza", "3", "Milestone Due", 0.15),

                  SizedBox(height: 20),

                  // SCHEDULE & SAFETY
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20.0),
                    child: Row(
                      children: [
                        Expanded(child: _buildSmallStatCard("Schedule", true)),
                        SizedBox(width: 15),
                        Expanded(child: _buildSmallStatCard("Safety", false)),
                      ],
                    ),
                  ),
                  SizedBox(height: 120),
                ],
              ),
            ),
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
                Text("Status: ", style: TextStyle(color: Colors.white38, fontSize: 10)),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(5)),
                  child: Text("Active", style: TextStyle(color: Colors.greenAccent, fontSize: 9, fontWeight: FontWeight.bold)),
                ),
              ],
            ),
            SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("Progress:", style: TextStyle(color: Colors.white38, fontSize: 10)),
                Text("72%", style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
              ],
            ),
            SizedBox(height: 5),
            LinearProgressIndicator(value: 0.72, backgroundColor: Colors.white12, valueColor: AlwaysStoppedAnimation(Colors.cyanAccent), minHeight: 4),
            Spacer(),
            Text("Code: ${project['code']}", style: TextStyle(color: Colors.white24, fontSize: 9)),
            Text(project['location'] ?? "No location", style: TextStyle(color: Colors.white38, fontSize: 9)),
          ],
        ),
      ),
    );
  }

  Widget _buildFeaturedProjectCard(String title, String num, String status, double progress) {
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
                      Text("Status: ", style: TextStyle(color: Colors.white38, fontSize: 10)),
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
                  Text("Nov 1 - Mar 26", style: TextStyle(color: Colors.white38, fontSize: 10)),
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
            onTap: () {},
            child: _navIcon(Icons.home, "Dashboard", true),
          ),
          GestureDetector(
            onTap: () {},
            child: _navIcon(Icons.folder, "Projects", false),
          ),
          GestureDetector(
            onTap: () => Navigator.pushNamed(context, '/history'),
            child: _navIcon(Icons.description, "Reports", false),
          ),
          GestureDetector(
            onTap: () {},
            child: _navIcon(Icons.people, "Team", false),
          ),
          GestureDetector(
            onTap: () {},
            child: _navIcon(Icons.person, "Profile", false),
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
}
