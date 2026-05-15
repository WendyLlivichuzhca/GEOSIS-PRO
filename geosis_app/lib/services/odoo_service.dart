import 'dart:convert';
import 'package:http/http.dart' as http;

class OdooService {
  final String baseUrl = "https://geosis.corporativoqbank.com";
  String? sessionId;

  Future<bool> login(String username, String password) async {
    final response = await http.post(
      Uri.parse("$baseUrl/web/session/authenticate"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "jsonrpc": "2.0",
        "params": {
          "db": "odoo-final",
          "login": username,
          "password": password
        }
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['result'] != null) {
        sessionId = response.headers['set-cookie'];
        return true;
      }
    }
    return false;
  }

  Future<List<dynamic>> getProjects() async {
    try {
      final response = await http.post(
        Uri.parse("$baseUrl/web/geosis/projects"),
        headers: {
          "Content-Type": "application/json",
          "Cookie": sessionId ?? ""
        },
        body: jsonEncode({
          "jsonrpc": "2.0",
          "params": {}
        }),
      );

      print("DEBUG: Status Odoo Proyectos: ${response.statusCode}");
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        print("DEBUG: Respuesta Odoo: ${data['result']}");
        if (data['result'] != null && data['result']['status'] == 'success') {
          return data['result']['data'];
        }
      }
    } catch (e) {
      print("DEBUG: Error cargando proyectos: $e");
    }
    return [];
  }
  Future<bool> submitReport(Map<String, dynamic> reportData) async {
    final response = await http.post(
      Uri.parse("$baseUrl/geosis/mobile/submit_report"),
      headers: {
        "Content-Type": "application/json",
        "Cookie": sessionId ?? ""
      },
      body: jsonEncode({
        "jsonrpc": "2.0",
        "params": {"report": reportData}
      }),
    );
    
    return response.statusCode == 200;
  }
}
