import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class OdooService {
  final String baseUrl = "https://geosis.corporativoqbank.com";
  final String database = "odoo-final";
  String? sessionId;

  String _extractSessionCookie(String rawCookie) {
    return rawCookie
        .split(',')
        .map((part) => part.trim().split(';').first)
        .firstWhere(
          (part) => part.startsWith('session_id='),
          orElse: () => rawCookie.split(';').first.trim(),
        );
  }

  Future<void> _loadSession() async {
    if (sessionId != null && sessionId!.isNotEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    sessionId = prefs.getString('odoo_session_cookie');
  }

  Future<void> _saveSession(String cookie) async {
    final prefs = await SharedPreferences.getInstance();
    sessionId = cookie;
    await prefs.setString('odoo_session_cookie', cookie);
  }

  Future<bool> login(String username, String password) async {
    final response = await http.post(
      Uri.parse("$baseUrl/web/session/authenticate"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "jsonrpc": "2.0",
        "params": {
          "db": database,
          "login": username,
          "password": password
        }
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      if (data['result'] != null) {
        final cookie = response.headers['set-cookie'];
        if (cookie == null || cookie.isEmpty) return false;
        await _saveSession(_extractSessionCookie(cookie));
        return true;
      }
    }
    return false;
  }

  Future<List<dynamic>> getProjects() async {
    try {
      await _loadSession();
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
    try {
      await _loadSession();
      final response = await http.post(
        Uri.parse("$baseUrl/web/geosis/submit_report"),
        headers: {
          "Content-Type": "application/json",
          "Cookie": sessionId ?? ""
        },
        body: jsonEncode({
          "jsonrpc": "2.0",
          "params": {"report": reportData}
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['result'] != null && data['result']['status'] == 'success') {
          print("DEBUG: Reporte subido exitosamente: ${data['result']['message']}");
          return true;
        } else {
          print("DEBUG: Error de Odoo en submitReport: ${data['result'] != null ? data['result']['message'] : data['error']}");
        }
      }
    } catch (e) {
      print("DEBUG: Excepción en submitReport: $e");
    }
    return false;
  }

  Future<List<dynamic>> getBitacoras({int? projectId}) async {
    try {
      await _loadSession();
      final response = await http.post(
        Uri.parse("$baseUrl/web/geosis/bitacoras"),
        headers: {
          "Content-Type": "application/json",
          "Cookie": sessionId ?? ""
        },
        body: jsonEncode({
          "jsonrpc": "2.0",
          "params": projectId != null ? {"project_id": projectId} : {}
        }),
      );

      print("DEBUG: Status Odoo getBitacoras: ${response.statusCode}");
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['result'] != null && data['result']['status'] == 'success') {
          return data['result']['data'];
        }
      }
    } catch (e) {
      print("DEBUG: Error cargando historial de bitacoras: $e");
    }
    return [];
  }

  Future<void> saveOfflineReport(Map<String, dynamic> report) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_bitacora_drafts');
      List<dynamic> drafts = [];
      if (rawDrafts != null) {
        drafts = jsonDecode(rawDrafts);
      }
      report['offline_id'] = DateTime.now().millisecondsSinceEpoch.toString();
      drafts.add(report);
      await prefs.setString('offline_bitacora_drafts', jsonEncode(drafts));
      print("DEBUG: Reporte offline guardado. Total en cola: ${drafts.length}");
    } catch (e) {
      print("DEBUG: Error al guardar reporte offline: $e");
    }
  }

  Future<List<dynamic>> getOfflineReports() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_bitacora_drafts');
      if (rawDrafts != null) {
        return jsonDecode(rawDrafts);
      }
    } catch (e) {
      print("DEBUG: Error cargando borradores offline: $e");
    }
    return [];
  }

  Future<void> removeOfflineReport(String offlineId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_bitacora_drafts');
      if (rawDrafts != null) {
        List<dynamic> drafts = jsonDecode(rawDrafts);
        drafts.removeWhere((item) => item['offline_id'] == offlineId);
        await prefs.setString('offline_bitacora_drafts', jsonEncode(drafts));
      }
    } catch (e) {
      print("DEBUG: Error eliminando borrador offline: $e");
    }
  }

  Future<Map<String, int>> syncOfflineReports() async {
    int successCount = 0;
    int failCount = 0;
    try {
      final drafts = await getOfflineReports();
      if (drafts.isEmpty) return {'success': 0, 'fail': 0};

      final List<dynamic> reportsToSync = List.from(drafts);
      for (var report in reportsToSync) {
        final String offlineId = report['offline_id'];
        final Map<String, dynamic> odooData = Map.from(report);
        odooData.remove('offline_id');

        bool success = await submitReport(odooData);
        if (success) {
          successCount++;
          await removeOfflineReport(offlineId);
        } else {
          failCount++;
        }
      }
    } catch (e) {
      print("DEBUG: Error en proceso de sincronización offline: $e");
    }
    return {'success': successCount, 'fail': failCount};
  }

  Future<List<dynamic>> getAvaluos() async {
    try {
      await _loadSession();
      final response = await http.post(
        Uri.parse("$baseUrl/web/geosis/avaluos"),
        headers: {
          "Content-Type": "application/json",
          "Cookie": sessionId ?? ""
        },
        body: jsonEncode({
          "jsonrpc": "2.0",
          "params": {}
        }),
      );

      print("DEBUG: Status Odoo Avaluos: ${response.statusCode}");
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['result'] != null && data['result']['status'] == 'success') {
          return data['result']['data'];
        }
      }
    } catch (e) {
      print("DEBUG: Error cargando avalúos: $e");
    }
    return [];
  }

  Future<Map<String, dynamic>?> submitAvaluo(Map<String, dynamic> avaluoData) async {
    try {
      await _loadSession();
      final response = await http.post(
        Uri.parse("$baseUrl/web/geosis/submit_avaluo"),
        headers: {
          "Content-Type": "application/json",
          "Cookie": sessionId ?? ""
        },
        body: jsonEncode({
          "jsonrpc": "2.0",
          "params": {"avaluo": avaluoData}
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['result'] != null && data['result']['status'] == 'success') {
          print("DEBUG: Avalúo subido exitosamente: ${data['result']['message']}");
          return data['result'];
        } else {
          print("DEBUG: Error de Odoo en submitAvaluo: ${data['result'] != null ? data['result']['message'] : data['error']}");
        }
      }
    } catch (e) {
      print("DEBUG: Excepción en submitAvaluo: $e");
    }
    return null;
  }

  Future<void> saveOfflineAvaluo(Map<String, dynamic> avaluo) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_avaluo_drafts');
      List<dynamic> drafts = [];
      if (rawDrafts != null) {
        drafts = jsonDecode(rawDrafts);
      }
      avaluo['offline_id'] = DateTime.now().millisecondsSinceEpoch.toString();
      drafts.add(avaluo);
      await prefs.setString('offline_avaluo_drafts', jsonEncode(drafts));
      print("DEBUG: Avalúo offline guardado. Total en cola: ${drafts.length}");
    } catch (e) {
      print("DEBUG: Error al guardar avalúo offline: $e");
    }
  }

  Future<List<dynamic>> getOfflineAvaluos() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_avaluo_drafts');
      if (rawDrafts != null) {
        return jsonDecode(rawDrafts);
      }
    } catch (e) {
      print("DEBUG: Error cargando borradores offline de avalúos: $e");
    }
    return [];
  }

  Future<void> removeOfflineAvaluo(String offlineId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final String? rawDrafts = prefs.getString('offline_avaluo_drafts');
      if (rawDrafts != null) {
        List<dynamic> drafts = jsonDecode(rawDrafts);
        drafts.removeWhere((item) => item['offline_id'] == offlineId);
        await prefs.setString('offline_avaluo_drafts', jsonEncode(drafts));
      }
    } catch (e) {
      print("DEBUG: Error eliminando borrador offline de avalúo: $e");
    }
  }

  Future<Map<String, int>> syncOfflineAvaluos() async {
    int successCount = 0;
    int failCount = 0;
    try {
      final drafts = await getOfflineAvaluos();
      if (drafts.isEmpty) return {'success': 0, 'fail': 0};

      final List<dynamic> avaluosToSync = List.from(drafts);
      for (var av in avaluosToSync) {
        final String offlineId = av['offline_id'];
        final Map<String, dynamic> odooData = Map.from(av);
        odooData.remove('offline_id');

        final result = await submitAvaluo(odooData);
        if (result != null && result['status'] == 'success') {
          successCount++;
          await removeOfflineAvaluo(offlineId);
        } else {
          failCount++;
        }
      }
    } catch (e) {
      print("DEBUG: Error en proceso de sincronización offline de avalúos: $e");
    }
    return {'success': successCount, 'fail': failCount};
  }
}
