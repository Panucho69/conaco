// Formularios de inicio de sesión y registro: mostrar contraseña y revisar requisitos mientras se escribe
document.querySelectorAll('.ver-clave').forEach(function (boton) {
  boton.addEventListener('click', function () {
    var input = boton.parentElement.querySelector('input');
    var visible = input.type === 'text';
    input.type = visible ? 'password' : 'text';
    boton.setAttribute('aria-label', visible ? 'Mostrar contraseña' : 'Ocultar contraseña');
    boton.querySelector('i').className = visible ? 'bi bi-eye' : 'bi bi-eye-slash';
  });
});

(function () {
  var clave = document.getElementById('password1');
  var repetir = document.getElementById('password2');
  var usuario = document.getElementById('username');
  if (!clave || !repetir) return;
  var reglas = document.querySelectorAll('.reglas-clave li');
  var aviso = document.querySelector('.coincide');

  function revisar() {
    var valor = clave.value;
    var ok = {
      largo: valor.length >= 8,
      letras: valor.length > 0 && !/^\d+$/.test(valor),
      usuario: valor.length > 0 && valor.toLowerCase() !== usuario.value.trim().toLowerCase()
    };
    reglas.forEach(function (li) {
      li.classList.toggle('cumple', ok[li.dataset.regla]);
    });

    if (!repetir.value) {
      aviso.textContent = '';
      aviso.className = 'coincide';
    } else if (repetir.value === valor) {
      aviso.textContent = 'Las contraseñas coinciden.';
      aviso.className = 'coincide si';
    } else {
      aviso.textContent = 'Las contraseñas todavía no coinciden.';
      aviso.className = 'coincide no';
    }
  }
  [clave, repetir, usuario].forEach(function (el) { el.addEventListener('input', revisar); });
})();
