import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/bitacora_form_screen.dart';
import 'screens/bitacora_history_screen.dart';

void main() {
  runApp(GeosisApp());
}

class GeosisApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GEOSIS Mobile',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.blue,
        textTheme: GoogleFonts.outfitTextTheme(Theme.of(context).textTheme),
        scaffoldBackgroundColor: Color(0xFF0D1B2A),
      ),
      initialRoute: '/login',
      routes: {
        '/login': (context) => LoginScreen(),
        '/dashboard': (context) => DashboardScreen(),
        '/form': (context) => BitacoraFormScreen(),
        '/history': (context) => BitacoraHistoryScreen(),
      },
    );
  }
}
