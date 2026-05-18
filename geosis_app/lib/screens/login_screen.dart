import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../services/odoo_service.dart';
import 'dart:ui';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final odoo = OdooService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // FONDO (Igual a la imagen)
          Container(
            decoration: BoxDecoration(
              image: DecorationImage(
                image: NetworkImage('https://images.unsplash.com/photo-1504307651254-35680f356dfd?q=80&w=1000'), 
                fit: BoxFit.cover,
              ),
            ),
          ),
          // Filtro Azul Oscuro Premium
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0D1B2E).withOpacity(0.8),
                  Color(0xFF0D1B2E).withOpacity(0.95),
                ],
              ),
            ),
          ),

          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 40.0),
              child: Column(
                children: [
                  SizedBox(height: 50),
                  // LOGO GEOSIS
                  _buildLogo(),
                  SizedBox(height: 60),

                  // CAMPOS DE TEXTO (Estilo Cristal con Brillo)
                  _buildGlassInput("Correo Electrónico", Icons.email_outlined, _emailController),
                  SizedBox(height: 20),
                  _buildGlassInput("Contraseña", Icons.lock_outline, _passwordController, isPass: true),

                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      onPressed: () {},
                      child: Text("¿Olvidaste tu contraseña?", style: TextStyle(color: Colors.white38, fontSize: 13)),
                    ),
                  ),
                  SizedBox(height: 30),

                  // BOTON SIGN IN (Funcional)
                  _buildSignInButton(),
                  
                  SizedBox(height: 20),
                  _buildSocialButton("Iniciar sesión con Microsoft 365", Icons.grid_view_rounded, Colors.orange),
                  SizedBox(height: 15),
                  _buildSocialButton("SSO (Inicio Único)", null, null),

                  SizedBox(height: 40),
                  GestureDetector(
                    onTap: () {},
                    child: RichText(
                      text: TextSpan(
                        text: "¿No tienes una cuenta? ",
                        style: TextStyle(color: Colors.white54),
                        children: [
                          TextSpan(text: "Contacta al Admin.", style: TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLogo() {
    return Column(
      children: [
        Container(
          padding: EdgeInsets.all(15),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: Colors.cyanAccent.withOpacity(0.5), width: 2),
            boxShadow: [BoxShadow(color: Colors.cyanAccent.withOpacity(0.2), blurRadius: 20)],
          ),
          child: Icon(Icons.engineering, color: Colors.cyanAccent, size: 50),
        ),
        SizedBox(height: 15),
        Text("GEOSIS", style: GoogleFonts.outfit(color: Colors.white, fontSize: 42, fontWeight: FontWeight.bold, letterSpacing: 3)),
        Text("GESTIÓN DE CONSTRUCCIÓN", style: GoogleFonts.outfit(color: Colors.white54, fontSize: 11, letterSpacing: 2)),
      ],
    );
  }

  Widget _buildGlassInput(String hint, IconData icon, TextEditingController controller, {bool isPass = false}) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(15),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.05),
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: TextField(
            controller: controller,
            obscureText: isPass,
            style: TextStyle(color: Colors.white),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: Colors.white38),
              prefixIcon: Icon(icon, color: Colors.white38),
              suffixIcon: isPass ? Icon(Icons.visibility_off_outlined, color: Colors.white24) : null,
              border: InputBorder.none,
              contentPadding: EdgeInsets.symmetric(vertical: 20),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSignInButton() {
    return SizedBox(
      width: double.infinity,
      height: 55,
      child: ElevatedButton(
        onPressed: () async {
          showDialog(context: context, builder: (c) => Center(child: CircularProgressIndicator()));
          bool success = await odoo.login(_emailController.text.trim(), _passwordController.text.trim());
          Navigator.pop(context);
          if (success) {
            Navigator.pushReplacementNamed(context, '/dashboard');
          } else {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text("Credenciales incorrectas")));
          }
        },
        style: ElevatedButton.styleFrom(
          backgroundColor: Color(0xFF1B3A5E),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
        ),
        child: Text("Iniciar Sesión", style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
      ),
    );
  }

  Widget _buildSocialButton(String text, IconData? icon, Color? iconColor) {
    return Container(
      width: double.infinity,
      height: 55,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.white12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (icon != null) ...[Icon(icon, color: iconColor, size: 20), SizedBox(width: 10)],
          Text(text, style: GoogleFonts.outfit(color: Colors.white, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
