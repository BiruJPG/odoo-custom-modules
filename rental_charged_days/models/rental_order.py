from odoo import api, fields, models
from odoo.exceptions import ValidationError

class RentalOrder(models.Model):
    _inherit = 'sale.order'

    rental_charged_days = fields.Integer(
        string='Días Cobrados',
        compute='_compute_rental_charged_days',
        store=True,
        readonly=False,
        help='Días efectivamente cobrados al cliente. '
             'Puede diferir del período logístico (retiro/devolución).'
    )

    @api.depends('rental_start_date', 'rental_return_date')
    def _compute_rental_charged_days(self):
        """Calcula los días del período como valor por defecto,
           pero permite sobreescritura manual."""
        for order in self:
            if order.rental_start_date and order.rental_return_date:
                delta = order.rental_return_date - order.rental_start_date
                order.rental_charged_days = max(delta.days, 1)
            else:
                order.rental_charged_days = 1

    @api.constrains('rental_charged_days')
    def _check_rental_charged_days(self):
        for order in self:
            if order.is_rental_order and order.rental_charged_days < 1:
                raise ValidationError(
                    'Los días cobrados deben ser al menos 1.'
                )


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Permite que las líneas de alquiler usen los días cobrados
    # en lugar de la duración real del período
    @api.depends(
        'order_id.rental_charged_days',
        'order_id.rental_start_date',
        'order_id.rental_return_date',
        'product_id',
        'rental_uom',
    )
    def _compute_price_unit(self):
        """Sobreescribe el precio usando días cobrados si está definido."""
        super()._compute_price_unit()
        for line in self:
            order = line.order_id
            if (
                order.is_rental_order
                and order.rental_charged_days
                and order.rental_start_date
                and order.rental_return_date
            ):
                real_days = max(
                    (order.rental_return_date - order.rental_start_date).days,
                    1
                )
                charged_days = order.rental_charged_days

                if real_days != charged_days and real_days > 0:
                    # Ajusta el precio proporcionalmente
                    line.price_unit = line.price_unit * charged_days / real_days
