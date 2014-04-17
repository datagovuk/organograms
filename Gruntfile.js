module.exports = function(grunt) {
  var pkg = grunt.file.readJSON('package.json');

  grunt.loadNpmTasks('grunt-contrib-less');
  grunt.loadNpmTasks('grunt-contrib-copy');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-contrib-coffee');

  // Project configuration.
  grunt.initConfig({
    pkg: pkg,
    less: {
      options: { yuicompress: true },
      page: {
        src: [ 
          'src/less/bootstrap-3.0.0.css',
          'src/less/page.less',
          'src/less/chosen.min.css'
        ],
        dest: 'public/css/page.min.css'
      },
      viz: {
        src: 'src/less/organograms.less',
        dest: 'public/css/organograms.min.css',
      }
    },
    watch: {
      styles: {
        files: 'src/less/**/*.less',
        tasks: 'less'
      },
      coffee: {
        files: 'src/coffee/**/*.coffee',
        tasks: 'coffee'
      },
    },
    copy: {
      vendorscripts: {
        expand: true,
        cwd: 'src/coffee/vendor/',
        src: '**/*',
        dest: 'public/scripts/vendor/',
      },
      chosensprite: {
        expand: true,
        cwd: 'src/images/',
        src: 'chosen-sprite*',
        dest: 'public/css/',
      },
      images: {
        expand: true,
        cwd: 'src/images/',
        src: '**/*.gif',
        dest: 'public/images/',
      }
    },
    coffee: {
      build: {
        src: [
          'src/coffee/lib/*.coffee',
          'src/coffee/organograms.coffee',
        ],
        dest: 'public/scripts/organograms.min.js'
      }
    }
  });

  // Default task(s).
  grunt.registerTask('default', ['less','copy','coffee']);
};
