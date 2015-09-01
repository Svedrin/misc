// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

var fluxmon = angular.module('FluxmonApp', ['ui.router', 'angular-flot', 'ui.tree']);

fluxmon.config(function($interpolateProvider, $stateProvider, $urlRouterProvider) {
    $interpolateProvider.startSymbol('{[');
    $interpolateProvider.endSymbol(']}');

    $urlRouterProvider.otherwise("/index");

    $stateProvider
        .state('index', {
            url: "/index",
            template: "&nbsp;"
        })
        .state('search', {
            url: "/search/:query",
            templateUrl: "static/templates/search.html",
            controller:  "SearchCtrl"
        })
        .state('tree', {
            url: "/tree",
            templateUrl: "static/templates/domain-tree.html",
            controller: "DomainTreeCtrl"
        })
        .state('domain', {
            url: "/domain/:domId",
            templateUrl: "static/templates/domain.html",
            controller:  "DomainCtrl"
        })
        .state('domain.add-host', {
            url: "/add",
            templateUrl: "static/templates/domain-addhost.html"
        })
        .state('domain.aggregatelist', {
            url: "/aggr/list",
            templateUrl: "static/templates/domain-aggregatelist.html",
            controller:  "DomainAggregateListCtrl"
        })
        .state('domain.aggregate', {
            url: "/aggr/:name",
            templateUrl: "static/templates/domain-aggregate.html",
            controller:  "DomainAggregateCtrl"
        })
        .state('node', {
            url: "/node/:nodeId",
            templateUrl: "static/templates/node.html",
            controller:  "NodeCtrl"
        })
        .state('node.checklist', {
            url: '/list',
            templateUrl: "static/templates/node-checklist.html",
            controller:  "NodeCheckListCtrl"
        })
        .state('node.check', {
            url: "/:check",
            templateUrl: "static/templates/node-check.html",
            controller:  "NodeCheckCtrl"
        })
        .state('node.check.varlist', {
            url: "/list",
            templateUrl: "static/templates/node-check-varlist.html"
        })
        .state('node.check.view', {
            url: "/view/:name",
            templateUrl: "static/templates/node-check-view.html"
        })
        .state('node.check.variable', {
            url: "/var/:name",
            templateUrl: "static/templates/node-check-var.html",
            controller:  "NodeCheckVarCtrl"
        });
});

fluxmon.run(function($rootScope, $state){
  $rootScope.showIndex = function(){
    return $state.is('index');
  };
});

fluxmon.directive('ngEnter', function () {
  return function (scope, element, attrs) {
    element.bind("keydown keypress", function (event) {
      if(event.which === 13) {
        scope.$apply(function (){
          scope.$eval(attrs.ngEnter);
        });
        event.preventDefault();
      }
    });
  };
});


fluxmon.service("isMobile", function(){
    var isMobile = {
        Android: function() {
            return navigator.userAgent.match(/Android/i);
        },
        BlackBerry: function() {
            return navigator.userAgent.match(/BlackBerry/i);
        },
        iOS: function() {
            return navigator.userAgent.match(/iPhone|iPad|iPod/i);
        },
        Opera: function() {
            return navigator.userAgent.match(/Opera Mini/i);
        },
        Windows: function() {
            return navigator.userAgent.match(/IEMobile/i);
        },
        any: function() {
            return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Opera() || isMobile.Windows());
        }
    };
    return isMobile;
});

fluxmon.controller("GraphCtrl", function($scope, $interval){
    var self = this;

    $scope.zoomTo = function(args){
        // When zooming in, we're called as:
        //   zoomTo({start: <start>, end: <end>})
        // When zooming back out or saved_* values change, we're called as:
        //   zoomTo()

        // Set defaults
        var args    = args || {}
        var start   = args.start   || 0;
        var end     = args.end     || self.saved_end;
        var profile = args.profile || self.saved_profile;

        // Known start overwrites the profile
        if( start ){
            profile = null;
        }
        else{
            start = end - profile.duration;
            if( end == self.saved_end ){
                $scope.new_data_available = false;
            }
        }

        $scope.start = start;
        $scope.end   = end;
        $scope.active_profile = profile;
    }

    $scope.prediction = true;
    $scope.new_data_available = false;

    // Initialize end

    $interval(function(){
        var old_saved_end = self.saved_end;
        // See if we need to update saved_end...
        while( new Date() > (self.saved_end + 300) * 1000 ){
            self.saved_end += 300;
        }
        // ...and if we updated it, call zoomTo() to update the images
        if( old_saved_end != self.saved_end ){
            if( $scope.active_profile ){
                $scope.zoomTo();
            }
            else{
                $scope.new_data_available = true;
            }
        }
    }, 1000);

    $scope.set_end = function(end){
        self.saved_end = end;
        $scope.zoomTo();
    };

    // Initialize profiles
    $scope.profiles = [
        {title:  "4h", duration:      6*60*60, tiny: true },
        {title: "24h", duration:     24*60*60, tiny: true },
        {title: "48h", duration:     48*60*60, tiny: true },
        {title:  "1w", duration:   7*24*60*60, tiny: true },
        {title:  "2w", duration:  14*24*60*60, tiny: false},
        {title:  "1m", duration:  30*24*60*60, tiny: true },
        {title:  "3m", duration:  90*24*60*60, tiny: false},
        {title:  "6m", duration: 180*24*60*60, tiny: false},
        {title:  "1y", duration: 365*24*60*60, tiny: true },
    ];
    $scope.set_active_profile = function(val){
        self.saved_profile = val;
        if( self.saved_profile != $scope.active_profile ){
            $scope.zoomTo();
        }
    }
    $scope.set_active_profile($scope.profiles[1]); //24h

});
