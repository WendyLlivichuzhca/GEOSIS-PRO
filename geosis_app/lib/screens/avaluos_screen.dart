import 'dart:convert';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/odoo_service.dart';
import 'avaluo_form_screen.dart';

class AvaluosScreen extends StatefulWidget {
  @override
  _AvaluosScreenState createState() => _AvaluosScreenState();
}

class _AvaluosScreenState extends State<AvaluosScreen> {
  final odoo = OdooService();
  List<dynamic> avaluos = [];
  List<dynamic> filteredAvaluos = [];
  String searchQuery = "";
  String selectedFilter = "Todos"; // Todos, draft, inspected, calculated
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => isLoading = true);
    try {
      final list = await odoo.getAvaluos();
      setState(() {
        avaluos = list;
        _applyFilters(list);
        isLoading = false;
      });
    } catch (e) {
      print("DEBUG: Error al cargar listado de avalúos: $e");
      setState(() => isLoading = false);
    }
  }

  void _applyFilters(List<dynamic> rawList) {
    List<dynamic> temp = List.from(rawList);

    // Búsqueda por texto
    if (searchQuery.isNotEmpty) {
      temp = temp.where((av) {
        final code = (av['code'] ?? '').toString().toLowerCase();
        final title = (av['title'] ?? '').toString().toLowerCase();
        final owner = (av['owner_name'] ?? '').toString().toLowerCase();
        final location = (av['location'] ?? '').toString().toLowerCase();
        return code.contains(searchQuery.toLowerCase()) ||
            title.contains(searchQuery.toLowerCase()) ||
            owner.contains(searchQuery.toLowerCase()) ||
            location.contains(searchQuery.toLowerCase());
      }).toList();
    }

    // Filtro de pestaña/estado
    if (selectedFilter != "Todos") {
      String statusKey = "draft";
      if (selectedFilter == "Inspeccionados") statusKey = "inspected";
      if (selectedFilter == "Calculados") statusKey = "calculated";

      temp = temp.where((av) => av['state'] == statusKey).toList();
    }

    setState(() {
      filteredAvaluos = temp;
    });
  }

  void _onSearchChanged(String query) {
    searchQuery = query;
    _applyFilters(avaluos);
  }

  void _onFilterChanged(String filter) {
    selectedFilter = filter;
    _applyFilters(avaluos);
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
          "Avalúos Inmobiliarios",
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
          // Fondo gradiente estructural oscurecido
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
            child: Column(
              children: [
                // Barra de Búsqueda
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10),
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.04),
                      borderRadius: BorderRadius.circular(15),
                      border: Border.all(color: Colors.white.withOpacity(0.05)),
                    ),
                    child: TextField(
                      style: TextStyle(color: Colors.white, fontSize: 14),
                      onChanged: _onSearchChanged,
                      decoration: InputDecoration(
                        hintText: "Buscar por código, propietario, dirección...",
                        hintStyle: TextStyle(color: Colors.white24, fontSize: 13),
                        prefixIcon: Icon(Icons.search, color: Colors.white30),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(vertical: 15),
                      ),
                    ),
                  ),
                ),

                // Filtro de Chips Horizontales (Todos, draft, inspected, calculated)
                _buildFilterChips(),

                // Listado principal
                Expanded(
                  child: isLoading
                      ? Center(child: CircularProgressIndicator(color: Colors.cyanAccent))
                      : filteredAvaluos.isEmpty
                          ? _buildEmptyState()
                          : ListView.builder(
                              physics: BouncingScrollPhysics(),
                              padding: EdgeInsets.all(20),
                              itemCount: filteredAvaluos.length,
                              itemBuilder: (context, index) {
                                return _buildAvaluoCard(filteredAvaluos[index]);
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

  Widget _buildFilterChips() {
    final filters = ["Todos", "Pendientes", "Inspeccionados", "Calculados"];
    return Container(
      height: 50,
      padding: EdgeInsets.symmetric(vertical: 6),
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: EdgeInsets.only(left: 20),
        itemCount: filters.length,
        itemBuilder: (context, index) {
          final filter = filters[index];
          final isSelected = selectedFilter == filter;
          return GestureDetector(
            onTap: () => _onFilterChanged(filter),
            child: Container(
              margin: EdgeInsets.only(right: 12),
              padding: EdgeInsets.symmetric(horizontal: 18, vertical: 6),
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
                  filter,
                  style: GoogleFonts.outfit(
                    color: isSelected ? Colors.white : Colors.white70,
                    fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    fontSize: 12,
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.location_city_outlined, size: 80, color: Colors.white24),
          SizedBox(height: 15),
          Text(
            "No se encontraron avalúos",
            style: GoogleFonts.outfit(color: Colors.white70, fontSize: 16, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 5),
          Text(
            "Los registros de avalúos comerciales aparecerán aquí.",
            textAlign: TextAlign.center,
            style: GoogleFonts.outfit(color: Colors.white38, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildAvaluoCard(dynamic av) {
    final state = av['state'] ?? 'draft';
    final String code = av['code'] ?? 'AV-000';
    final String title = av['title'] ?? 'Avalúo General';
    final String owner = av['owner_name'] ?? 'Propietario no definido';
    final String location = av['location'] ?? 'Sin ubicación';
    final String dateStr = av['date'] ?? '';

    Color stateColor;
    String stateLabel;
    if (state == 'calculated') {
      stateColor = Colors.purpleAccent;
      stateLabel = "CALCULADO";
    } else if (state == 'inspected') {
      stateColor = Colors.blueAccent;
      stateLabel = "INSPECCIONADO";
    } else {
      stateColor = Colors.orangeAccent;
      stateLabel = "PENDIENTE";
    }

    return GestureDetector(
      onTap: () => _handleCardTap(av),
      child: Container(
        margin: EdgeInsets.only(bottom: 16),
        padding: EdgeInsets.all(18),
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
                  code,
                  style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 14),
                ),
                Container(
                  padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: stateColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: stateColor, width: 1),
                  ),
                  child: Text(
                    stateLabel,
                    style: GoogleFonts.outfit(
                      color: stateColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            SizedBox(height: 10),
            Text(
              title,
              style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
            ),
            SizedBox(height: 5),
            Row(
              children: [
                Icon(Icons.person_outline, size: 14, color: Colors.white54),
                SizedBox(width: 5),
                Text("Prop: $owner", style: GoogleFonts.outfit(color: Colors.white70, fontSize: 12)),
              ],
            ),
            SizedBox(height: 3),
            Row(
              children: [
                Icon(Icons.location_on_outlined, size: 14, color: Colors.white38),
                SizedBox(width: 5),
                Expanded(
                  child: Text(
                    location,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: GoogleFonts.outfit(color: Colors.white54, fontSize: 12),
                  ),
                ),
              ],
            ),
            if (dateStr.isNotEmpty) ...[
              SizedBox(height: 3),
              Row(
                children: [
                  Icon(Icons.calendar_today_outlined, size: 14, color: Colors.white38),
                  SizedBox(width: 5),
                  Text("Fecha: $dateStr", style: GoogleFonts.outfit(color: Colors.white38, fontSize: 11)),
                ],
              ),
            ],
            SizedBox(height: 12),
            Divider(color: Colors.white10),
            SizedBox(height: 6),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  state == 'draft' ? "Comenzar Inspección" : "Ver Resultados",
                  style: GoogleFonts.outfit(
                    color: state == 'draft' ? Colors.orangeAccent : Colors.cyanAccent,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Icon(
                  Icons.arrow_forward_ios_outlined,
                  size: 14,
                  color: state == 'draft' ? Colors.orangeAccent : Colors.cyanAccent,
                )
              ],
            )
          ],
        ),
      ),
    );
  }

  void _handleCardTap(dynamic av) {
    final state = av['state'] ?? 'draft';
    if (state == 'draft') {
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => AvaluoFormScreen(avaluo: av),
        ),
      ).then((_) => _loadData());
    } else {
      _showResultsDialog(av);
    }
  }

  void _showResultsDialog(dynamic av) {
    final String code = av['code'] ?? 'AV-000';
    final String title = av['title'] ?? 'Avalúo General';
    final double totalVal = (av['total_value'] ?? 0.0) as double;
    final double landVal = (av['land_value'] ?? 0.0) as double;
    final double constVal = (av['construction_value'] ?? 0.0) as double;
    final double depPercent = (av['construction_depreciation_percent'] ?? 0.0) as double;
    final int age = (av['construction_age'] ?? 0) as int;
    final String stateCoef = av['construction_state_coef'] ?? '1.00';

    String statusText = "Excelente (1.00)";
    if (stateCoef == '0.95') statusText = "Bueno (0.95)";
    if (stateCoef == '0.75') statusText = "Regular (0.75)";
    if (stateCoef == '0.40') statusText = "Malo (0.40)";
    if (stateCoef == '0.00') statusText = "Ruina (0.00)";

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: Color(0xFF0D1B2E),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(25),
          side: BorderSide(color: Colors.white10),
        ),
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              "RESULTADOS AVALÚO",
              style: GoogleFonts.outfit(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 1.5),
            ),
            SizedBox(height: 5),
            Text(
              "$code - $title",
              style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
            ),
          ],
        ),
        content: SingleChildScrollView(
          child: Column(
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
                    Text(
                      "VALOR COMERCIAL ESTIMADO",
                      style: GoogleFonts.outfit(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text(
                      "\$${totalVal.toStringAsFixed(2)} USD",
                      style: GoogleFonts.outfit(color: Colors.white, fontSize: 26, fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
              ),
              SizedBox(height: 20),
              _detailRow("Valor del Terreno:", "\$${landVal.toStringAsFixed(2)} USD"),
              _detailRow("Valor Construcción (Depreciada):", "\$${constVal.toStringAsFixed(2)} USD"),
              Divider(color: Colors.white10, height: 25),
              _detailRow("Depreciación Aplicada:", "${depPercent.toStringAsFixed(2)}%"),
              _detailRow("Antigüedad Edificación:", "$age Años"),
              _detailRow("Coeficiente Estado (Ross-Heidecke):", statusText),
            ],
          ),
        ),
        actions: [
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.cyanAccent,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
            onPressed: () => Navigator.pop(context),
            child: Text("Entendido", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: GoogleFonts.outfit(color: Colors.white54, fontSize: 12)),
          Text(value, style: GoogleFonts.outfit(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
