from rest_framework.generics import CreateAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from .serializers import ImagenSerializer, RegistroSerializer, PlatoSerializer, PedidoAddSerializer
from .models import DetallePedidoModel, PedidoModel, PlatoModel, UsuarioModel
from os import remove
from django.conf import settings
from django.db import transaction, Error


class RegistroController(CreateAPIView):
    serializer_class = RegistroSerializer

    def post(self, request: Request):
        data = self.serializer_class(data=request.data)

        if data.is_valid():
            data.save()
            return Response(data={
                'message': 'Usuario creado exitosamente',
                'content': data.data
            })
        else:
            return Response(data={
                'message': 'Error al crear el usuario',
                'content': data.errors
            })


class PlatosController(ListCreateAPIView):
    serializer_class = PlatoSerializer
    queryset = PlatoModel.objects.all()

    def post(self, request: Request):
        data = self.serializer_class(data=request.data)
        if data.is_valid():
            data.save()
            return Response(data={
                'content': data.data,
                'message': 'Plato creado exitosamente'
            })
        else:
            return Response(data={
                'message': 'Error al crear el plato',
                'content': data.errors
            }, status=400)

    def get(self, request):
        data = self.serializer_class(instance=self.get_queryset(), many=True)
        return Response(data = {
            "message":None,
            "content":data.data
        })

class SubirImagenController(CreateAPIView):
    serializer_class = ImagenSerializer

    def post(self, request: Request):
        print(request.FILES)
        data = self.serializer_class(data=request.FILES)

        if data.is_valid():
            archivo = data.save()
            url = request.META.get('HTTP_HOST')

            return Response(data={
                'message': 'Archivo subido exitosamente',
                'content': url + archivo
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(data={
                'message': 'Error al crear el archivo',
                'content': data.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class PlatoController(RetrieveUpdateDestroyAPIView):
    serializer_class = PlatoSerializer

    queryset = PlatoModel.objects.all()

    def get(self, request, id):
        plato_encontrado = self.get_queryset().filter(platoId=id).first()

        if not plato_encontrado:
            return Response(data={
                "message":"Plato no encontrado"
            }, status=status.HTTP_400_BAD_REQUEST)

        data = self.serializer_class(instance=plato_encontrado)

        return Response(data={
            "content": data.data
        })


    def delete(self, request, id):
        plato_encontrado : PlatoModel = self.get_queryset().filter(platoId=id).first()

        if not plato_encontrado:
            return Response(data={
                "message":"Plato no encontrado"
            }, status=status.HTTP_404_NOT_FOUND)          
        #plato_encontrado.delete()
        remove(settings.MEDIA_ROOT / str(plato_encontrado.platoFoto))

        data = PlatoModel.objects.filter(platoId = id).delete()
        print(data)
        return Response(data={
            "message":"Plato eliminado correctamente"
        })

class PedidoController(CreateAPIView):
    serializer_class = PedidoAddSerializer
    queryset = PedidoModel.objects.all()

    def post(self, request: Request):
        data = self.serializer_class(data=request.data)        
        
        try:
            if data.is_valid():
                detalles = data.validated_data.get("detalle")
                with transaction.atomic():
                    cliente : UsuarioModel =  UsuarioModel.objects.filter(usuarioId=data.validated_data.get("cliente_id")).first()
                    if cliente.usuarioTipo != 3:
                        raise Exception("El tipo de cliente no es valido")                    
                    
                    vendedor : UsuarioModel = UsuarioModel.objects.filter(usuarioId=data.validated_data.get("vendedor_id")).first()
                    if vendedor.usuarioTipo not in [1, 2]:
                        raise Exception("El tipo de vendedor no es valido")                    

                    nuevoPedido : PedidoModel = PedidoModel(pedidoTotal=0, cliente=cliente, vendedor=vendedor)
                    nuevoPedido.save()
                    total = 0
                    for detalle in detalles:
                        plato : PlatoModel = PlatoModel.objects.filter(platoId = detalle.get("plato_id")).first()                        
                        
                        if plato.platoCantidad < detalle.get("cantidad"):                            
                            raise Exception("Solo hay disponible {stock} plato(s) de {nombreProducto}".format(stock=plato.platoCantidad, nombreProducto=plato.platoNombre))

                        plato.platoCantidad -= detalle.get("cantidad")
                        plato.save()

                        nuevoDetalle : DetallePedidoModel = DetallePedidoModel(                            
                            detalleCantidad = detalle.get("cantidad"),
                            detalleSubTotal = detalle.get("cantidad") * plato.platoPrecio,
                            pedido = nuevoPedido,
                            plato = plato
                        )
                        nuevoDetalle.save()
                        total += nuevoDetalle.detalleSubTotal

                    nuevoPedido.pedidoTotal = total
                    nuevoPedido.save()

                    return Response(data={
                        'content': "pedido_id {pedidoId}".format(pedidoId=nuevoPedido.pedidoId),
                        'message': 'Pedido creado exitosamente'
                    }, status=status.HTTP_201_CREATED)
            else:
                raise Exception(data.errors)
        except Exception as e:
            return Response(data={
                'message': 'Error al crear el Pedido',
                'content': e.args[0]
            }, status=status.HTTP_400_BAD_REQUEST)

        

        

      
