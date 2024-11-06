from django.shortcuts import render, redirect
from .forms import TicketForm
import json
from .models import Ticket
from django.contrib import messages
from django.db import connection, transaction
from django.http import JsonResponse

class Nodo:
    def __init__(self, ticket):
        self.ticket = ticket
        self.siguiente = None


class TicketQueue:
    def __init__(self):
        self.frente = None
        self.final = None

    def cargar_tickets_desde_bd(self):
        self.frente = None
        self.final = None
        for ticket in Ticket.objects.all().order_by('id'):
            self.agregar_ticket(ticket)

    def agregar_ticket(self, ticket):
        nuevo_nodo = Nodo(ticket)

        if ticket.discapacidad:
            nuevo_nodo.siguiente = self.frente
            self.frente = nuevo_nodo
            if self.final is None:
                self.final = nuevo_nodo
        else:
            if self.frente is None:
                self.frente = nuevo_nodo
                self.final = nuevo_nodo
            else:
                self.final.siguiente = nuevo_nodo
                self.final = nuevo_nodo

    def mostrar_tickets(self):
        tickets_con_discapacidad = []
        tickets_sin_discapacidad = []
        nodo_actual = self.frente

        while nodo_actual:
            if nodo_actual.ticket.discapacidad:
                tickets_con_discapacidad.append(nodo_actual.ticket)
            else:
                tickets_sin_discapacidad.append(nodo_actual.ticket)
            nodo_actual = nodo_actual.siguiente

        return tickets_con_discapacidad + tickets_sin_discapacidad

    def ordenar_tickets(self, por='secuencia'):
        tickets = self.mostrar_tickets()

        tickets_con_discapacidad = [ticket for ticket in tickets if ticket.discapacidad]
        tickets_sin_discapacidad = [ticket for ticket in tickets if not ticket.discapacidad]

        def obtener_campo(ticket):
            if por == 'secuencia':
                return ticket.secuencia
            elif por == 'nombre':
                return ticket.nombre_cliente
            elif por == 'apellido':
                return ticket.apellido
            return None

        # Metodo de ordenamiento de burbuja
        def burbuja(lista, key_function):
            n = len(lista)
            for i in range(n):
                for j in range(0, n-i-1):
                    if key_function(lista[j]) > key_function(lista[j+1]):
                        lista[j], lista[j+1] = lista[j+1], lista[j]
            return lista

        tickets_con_discapacidad = burbuja(tickets_con_discapacidad, obtener_campo)
        tickets_sin_discapacidad = burbuja(tickets_sin_discapacidad, obtener_campo)

        return tickets_con_discapacidad + tickets_sin_discapacidad

    def buscar_ticket(self, busqueda):
        resultados = []
        nodo_actual = self.frente
        # Busqueda lineal
        while nodo_actual:
            if (str(nodo_actual.ticket.secuencia) == busqueda or
                    busqueda.lower() in nodo_actual.ticket.nombre_cliente.lower() or
                    busqueda.lower() in nodo_actual.ticket.apellido.lower()):
                resultados.append(nodo_actual.ticket)
            nodo_actual = nodo_actual.siguiente

        return resultados

    def atender_ticket(self, ticket_id):
        # Atender ticket eliminandolo de la cola
        if self.frente and self.frente.ticket.id == ticket_id:
            self.frente = self.frente.siguiente
            if self.frente is None:
                self.final = None
            return True

        # Buscar y eliminar en caso de estar en el medio de la cola
        nodo_actual = self.frente
        while nodo_actual and nodo_actual.siguiente:
            if nodo_actual.siguiente.ticket.id == ticket_id:
                nodo_actual.siguiente = nodo_actual.siguiente.siguiente
                if nodo_actual.siguiente is None:
                    self.final = nodo_actual
                return True
            nodo_actual = nodo_actual.siguiente

        return False

ticket_queue = TicketQueue()  # Instancia de la cola de tickets
def reorganizar_secuencia():
    tickets = list(Ticket.objects.all())
    n = len(tickets)
    for i in range(n):
        for j in range(0, n - i - 1):
            if tickets[j].secuencia > tickets[j + 1].secuencia:
                tickets[j], tickets[j + 1] = tickets[j + 1], tickets[j]

    for nueva_secuencia, ticket in enumerate(tickets, start=1):
        ticket.secuencia = nueva_secuencia
        ticket.save(update_fields=['secuencia'])


def reiniciar_id_ticket():
    if not Ticket.objects.exists():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='Ticket_ticket'")
            transaction.commit()


def agregar_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            reiniciar_id_ticket()
            ultimo_ticket = Ticket.objects.order_by('secuencia').last()
            nueva_secuencia = ultimo_ticket.secuencia + 1 if ultimo_ticket else 1
            ticket = form.save(commit=False)
            ticket.secuencia = nueva_secuencia
            ticket.save()
            ticket_queue.agregar_ticket(ticket)
            return redirect('ver_tickets')
    else:
        form = TicketForm()

    return render(request, 'agregar_ticket.html', {'form': form})


def ver_tickets(request):
    orden = request.GET.get('orden', request.session.get('orden', 'secuencia'))
    request.session['orden'] = orden
    busqueda = request.GET.get('buscar', '').strip()

    # Verifica si se ha solicitado la descarga o carga de JSON
    if request.method == 'POST':
        if 'descargar_json' in request.POST:
            return descargar_json()
        elif 'borrar_tickets' in request.POST:
            return borrar_tickets(request)
        elif 'cargar_tickets' in request.POST:
            if Ticket.objects.exists():
                messages.error(request, "La base de datos debe estar vacía para cargar tickets.")
            else:
                archivo_json = request.FILES.get('file')
                if archivo_json:
                    try:
                        datos = json.load(archivo_json)
                        for ticket_data in datos:
                            Ticket.objects.create(**ticket_data)
                        messages.success(request, "Tickets cargados exitosamente.")
                    except json.JSONDecodeError:
                        messages.error(request, "El archivo no es un JSON válido.")
                else:
                    messages.error(request, "No se ha seleccionado un archivo JSON.")
            return redirect('ver_tickets')

    # Cargar los tickets en la cola
    ticket_queue.frente = None
    for ticket in Ticket.objects.filter(aceptado=False).order_by('id'):
        ticket_queue.agregar_ticket(ticket)

    tickets = ticket_queue.ordenar_tickets(por=orden)
    primer_ticket = ticket_queue.frente.ticket if ticket_queue.frente else None

    if busqueda:
        tickets = ticket_queue.buscar_ticket(busqueda)
        if not tickets:  # Si no se encuentran tickets
            messages.info(request, "No se han encontrado tickets que coincidan con la búsqueda.")

    return render(request, 'ver_tickets.html', {
        'primer_ticket': primer_ticket,
        'tickets': tickets,
        'busqueda': busqueda,
        'orden': orden,
        'messages': messages.get_messages(request),
    })


def aceptar_ticket(request):
    if request.method == 'POST':
        secuencia = request.POST.get('secuencia')
        if secuencia:
            try:
                ticket_atendido = Ticket.objects.get(secuencia=int(secuencia))
                ticket_atendido.aceptado = True  # Marcar como aceptado
                ticket_atendido.save()

                eliminado = ticket_queue.atender_ticket(ticket_atendido.id)

                if eliminado:
                    # Recargar la cola después de la eliminación y reorganizar
                    reorganizar_secuencia()
                    ticket_queue.cargar_tickets_desde_bd()
                    messages.success(request, f'Ticket {secuencia} de {ticket_atendido.nombre_cliente} ha sido aceptado')
                else:
                    messages.warning(request, 'El ticket no se pudo eliminar de la cola.')
            except Ticket.DoesNotExist:
                messages.warning(request, 'El ticket no se pudo encontrar para aceptar.')
        else:
            messages.warning(request, 'No se ha proporcionado un número de secuencia de ticket.')

    return redirect('ver_tickets')

def eliminar_ticket(request, ticket_id):
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.delete()
        reorganizar_secuencia()
        messages.success(request, f'Ticket {ticket.secuencia} de {ticket.nombre_cliente} ha sido eliminado')
    except Ticket.DoesNotExist:
        messages.error(request, 'El ticket no existe.')

    return redirect('ver_tickets')


def ver_aceptados(request):
    tickets_aceptados = Ticket.objects.filter(aceptado=True)
    return render(request, 'ver_aceptados.html', {'tickets': tickets_aceptados})

def descargar_json():
    tickets = Ticket.objects.all().values()
    response = JsonResponse(list(tickets), safe=False, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="tickets.json"'
    return response

def borrar_tickets(request):
    Ticket.objects.all().delete()
    messages.success(request, "Todos los tickets han sido eliminados.")
    return redirect('ver_tickets')
def home(request):
    return render(request, 'home.html')
