<html>
<head>
  <title>Contest entries</title>
  <style type="text/css">
    #images-container {
          display: grid;
          grid-gap: 10px;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    }
    #images-container img {
        width: 100%;
    }
    #images-container .thumbnail {
      position: relative;
      overflow: hidden;
      background-color: #ccc;
    }
    #images-container .thumbnail img {
        vertical-align: middle;
    }
    #images-container .caption {
      margin: 0;
      padding: 1em;
      position: absolute;
      z-index: 1;
      bottom: 0;
      left: 0;
      width: 100%;
      max-height: 100%;
      overflow: auto;
      box-sizing: border-box;
      transition: transform .5s;
      background: rgba(0, 0, 0, .7);
      color: rgb(255, 255, 255);
    }

    #images-container .caption-opened {
      transform: translateY(100%);
    }
  </style>
  <script type="text/javascript">
        function onHoverThumbnail(targetElement)
        {
            targetElement.children[1].classList.add('caption-opened');
        }
        function onLeaveThumbnail(targetElement)
        {
            targetElement.children[1].classList.remove('caption-opened');
        }
  </script>
</head>

<body>
  <h1>Contest entries</h1>
  <div id="images-container">
    {images}
  </div>
</body>

</html>