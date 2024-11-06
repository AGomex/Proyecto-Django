from django.db import models

class Ticket(models.Model):
    nombre_cliente = models.CharField(max_length=100)
    apellido = models.CharField(max_length=50)
    secuencia = models.IntegerField(unique=True, default=0)
    discapacidad = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    aceptado = models.BooleanField(default=False)  # Nuevo campo


    def __str__(self):
        return self.nombre_cliente
