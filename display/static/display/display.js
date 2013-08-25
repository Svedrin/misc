// kate: space-indent on; indent-width 2; replace-tabs on;

$("div.fluxeditable").children("div.fluxlabel").children("button").click(function(){
  var fluxeditable = $(this.parentNode.parentNode);
  fluxeditable.children("div.fluxlabel").addClass("fluxhidden");
  fluxeditable.children("div.fluxeditor").removeClass("fluxhidden");
  fluxeditable.children("div.fluxeditor").children("form").submit(function(){
    var self = this;
    $.ajax({
      type: "POST",
      url:  "/display/" + this.app.value + "/" + this.model.value + "/",
      data: {
        id:      this.objid.value,
        display: this.display.value,
      },
      dataType: "json",
      success: function(data){
        fluxeditable.children("div.fluxlabel").children("span").html(data.display || self.placeholder.value);
        fluxeditable.children("div.fluxlabel").removeClass("fluxhidden");
        fluxeditable.children("div.fluxeditor").addClass("fluxhidden");
      }});
    return false;
  });
});
