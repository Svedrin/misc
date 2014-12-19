// kate: space-indent on; indent-width 4; replace-tabs on; hl JavaScript;

var fluxmon = angular.module('FluxmonApp', []);

fluxmon.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{[');
    $interpolateProvider.endSymbol(']}');
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

})
