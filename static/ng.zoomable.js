// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

fluxmon.directive("zoomable", function(){
    return {
        restrict: "A",
        scope: {
            "zoomTo":  "&",
            "ngSrc":   "@",
        },
        replace: true,
        template: ['<div>',
            '<div id="imgselector" ',
                'style="background-color: rgba(30, 30, 220, 0.4); ',
                    'position: absolute; height: 153px; width: 1px; ',
                    'z-index: 100; visibility: hidden;">&nbsp;</div>',
            '<img ',
                'class="visible-md-inline visible-lg-inline" alt="graph" ',
                'style="margin: 0 auto" ',
                'ng-src="{[ ngSrc ]}" />',
            '</div>'].join(''),
        controller: function($scope){
            $scope.$watch("ngSrc", function(){
                console.log("ng-src changed: ", $scope.ngSrc);
            });
            $scope.zoomTo({"start": null, "end": null});
        }
    }
});
